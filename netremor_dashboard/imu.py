import os
import io
import math
import string
import struct
import multiprocessing

# Binary parsing characters for struct library:
UNSIGNED_SHORT_INT = 'H'
UNSIGNED_LONG_LONG = 'Q'
FLOAT_32_BIT       = 'f'
STRING_8_BIT       = 's'
BIG_ENDIAN         = '>'

# Bytes corresponding to the above types:
BYTES_PER_UNSIGNED_SHORT_INT = 2
BYTES_PER_UNSIGNED_LONG_LONG = 8
BYTES_PER_FLOAT_32_BIT       = 4
BYTES_PER_CHAR_8_BIT         = 1

# IMU file types:
DELTA_T_TYPE = BIG_ENDIAN + UNSIGNED_SHORT_INT
INITIAL_TIMESTAMP_TYPE = BIG_ENDIAN + UNSIGNED_LONG_LONG

def get_imu_string_type(text):
    return BIG_ENDIAN + str(len(text)) + STRING_8_BIT

def get_imu_values_type(columns_count):
    return BIG_ENDIAN + str(columns_count) + FLOAT_32_BIT


# Maximum type values:
MAX_UNSIGNED_SHORT_INT = 2**16

def wimu(csv_filepath, imu_filepath, delta_t, timestamp_threshold = None, timestamp_colname = "timestamp", separator = ","):
    """
    Parse IMU sensor data from a CSV file to a IMU file.

    Args:
        csv_filepath (str): Path of the file whose contents are going to be parsed to IMU format.
        imu_filepath (str): Path of the destination file of the parsed IMU data.
        delta_t (int): expected time increment (in milliseconds) between samples in the CSV file.
        delta_t_threshold(int): maximum time difference between samples in the CSV file to apply interpolation.
                                If this threshold is surpassed, the CSV file content will be splitted in different IMU files.
                                There will be as many IMU files as times this threshold is surpassed.
        timestamp_colname (str, optional): Name of the column that will be interpreted as the timestamp column. Defaults to "timestamp".
        separator (str, optional): Character that acts as a separator in the CSV file. Defaults to ",".

    Raises:
        ValueError: If delta_t argument exceeds the maximum unsigned short integer value or if it is negative.
        NameError: If the argument provided as the name of the timestamp column in the CSV file is not indeed in the CSV file header.
        
    Returns:
        list[str]: containing the file paths of the outputted files
    """
    
    if delta_t < 1 or delta_t > MAX_UNSIGNED_SHORT_INT or not isinstance(delta_t, int):
        raise ValueError("Delta t must be an integer between (between 1 and %s)." % (MAX_UNSIGNED_SHORT_INT))

    csv_file = open(csv_filepath, "r")
    imu_file = open(imu_filepath, "wb")
    
    imu_filepaths  = []
    imu_file_index = 0
    imu_dirname    = os.path.dirname(imu_filepath)
    imu_basename   = os.path.basename(imu_filepath)

    ######################################################################################################################################################
    # Write IMU file header:
    # - DELTA_TIMESTAMP:   time increment between samples (unsigned short integer - 2 bytes)
    # - INITIAL_TIMESTAMP: timestamp to which apply DELTA_T field to interpret samples time (unsigned long long integer - 8 bytes)
    # - COLUMN_NAMES:      names for each of the fields that form 1 sample, the CSV column names without timestamp. (string - 1 byte per char).
    #                      This field's length is variable. It will be formed by the column names separated by commas ','. The end of this field,
    #                      hence the end of the header and the beginning of the file is encoded by the null character '\x00'.
    ######################################################################################################################################################

    # Get column names (excluding timestamp) to store them in IMU file header:
    columns = csv_file.readline().split(separator)
    columns = list(map(lambda col: col.strip(), columns))

    try:
        timestamp_index = columns.index(timestamp_colname)
        
    except ValueError:
        raise NameError("Timestamp column name not in file header.")

    columns.remove(timestamp_colname)
    
    # This will be used for parsing values in the body of the file
    body_line_binary_format = get_imu_values_type(len(columns))
    
    columns = list(map(lambda col: "".join(filter(lambda char: char in string.ascii_lowercase, col.lower())), columns))
    columns = (",".join(columns) + "\0").encode("utf-8")
    
    # Get first timestamp to store it in IMU file header:
    initial_timestamp = int(csv_file.readline().split(",")[timestamp_index].strip())
    
    imu_file.write(get_imu_header(delta_t, initial_timestamp, columns))

    ###############################################################
    # Write IMU file body:
    # The timestamp field in the CSV file will be removed in each
    # line and then the remaining values will be encoded as 32 bit
    # float values (4 bytes * columns length / sample).
    ###############################################################

    # Start reading the file from the first line after the column names
    csv_file.seek(0)
    next(csv_file)
    
    # This variable will be used to check if the timestamp_threshold has been surpassed
    last_timestamp = None
    
    # This will be used to measure the extra time that has been added to the signal due to the interpolation process.
    # To prevent large difference between the real signal and the IMU-formatted signal, this value will be used to
    # skip interpolated samples.
    missing_time = 0

    for line in csv_file:
        
        # Split timestamp from the values that will be stored in the body file:
        values    = line.split(separator)
        timestamp = int(values[timestamp_index])
        del values[timestamp_index]
        
        values = [float(item) for item in values]
        
        # Check if file has to be changed or if interpolation has to be made.
        if last_timestamp is not None:
            
            gap = timestamp - last_timestamp
            missing_time += gap - delta_t
            
            # When timestamp threshold is surpassed, close current output file and create a new one:
            if timestamp_threshold is not None and gap > timestamp_threshold:
                missing_time = 0
                
                imu_file.close()
                imu_filepaths += [imu_filepath]
                
                # Rename imu filepath to prevent overwritting the last one:
                imu_file_index          += 1
                bare_basename, extension = imu_basename.split(".")
                next_imu_basename        = "%s-%s.%s" % (bare_basename, imu_file_index, extension)
                imu_filepath             = os.path.join(imu_dirname, next_imu_basename)
                
                imu_file = open(imu_filepath, "wb")
                imu_file.write(get_imu_header(delta_t, timestamp, columns))
                
            # Fill in missing values:
            elif missing_time >= delta_t:
    
                # interpolation_samples_amount = math.ceil(gap/delta_t)
                interpolation_samples_amount = math.floor(missing_time/delta_t) + 1
                missing_time    %= delta_t
            
                for interpolation_sample_index in range(1, interpolation_samples_amount):
                    interpolation_values      = [last_value + ((value - last_value)/interpolation_samples_amount)*interpolation_sample_index for last_value, value in zip(last_values, values)]
                    interpolation_output_line = struct.pack(body_line_binary_format, *interpolation_values)
                    imu_file.write(interpolation_output_line)

        
        last_timestamp = timestamp
        last_values    = values
        output_line    = struct.pack(body_line_binary_format, *values)
        imu_file.write(output_line)
        
    
    imu_filepaths += [imu_filepath]

    imu_file.close()
    csv_file.close()
    
    return imu_filepaths


def rimu(imu_filepath, output_filepath = None, timestamp_from = None, timestamp_to = None, step = 1, offset = 0, n_samples = None, only_header = False, only_timestamp_range = False):
    """
    Read data from IMU file.
    That data can be either returned as a list of values or written in a CSV file, if output_filepath is provided.

    Args:
        imu_filepath (str): Source file with the IMU data.
        output_filepath (str, optional): If provided, will store the values read from the IMU file in CSV format. Defaults to None.
        timestamp_from (int, optional): Samples before this timestamp will not be returned/written. Defaults to None.
        timestamp_to (int, optional): Samples after this timestamp will not be returned/written. Defaults to None.
        step (int, optional): Number of samples to move forward when reading the IMU file. Defaults to 1.
        offset (int, optional): Number of samples to skip at the beginning of the IMU file. Defaults to 0.
        only_header(bool, optional): If True, IMU file body won't be read and the function will return the data in the
                                     header as a tuple. Defaults to False.
    Returns:
        list[tuple[float]]: If output_filepath is provided, this function will return a list of tuples, each of one
        with one float value per column in the columns header of the IMU file, or per columns in the original CSV file
        excluding timestamp.
        The first tuple in the list will be a string be the name of the column for that position in the following tuples
        of the list.
    """
    imu_file = open(imu_filepath, "rb")
    
    output = []
    if output_filepath is not None:
        output = open(output_filepath, "w")

    ########################
    # Read IMU file header:
    ########################
    
    delta_t           = struct.unpack(DELTA_T_TYPE, imu_file.read(BYTES_PER_UNSIGNED_SHORT_INT))[0]
    initial_timestamp = struct.unpack(INITIAL_TIMESTAMP_TYPE, imu_file.read(BYTES_PER_UNSIGNED_LONG_LONG))[0]

    byte_columns = b''
    while (current_byte := imu_file.read(BYTES_PER_CHAR_8_BIT)) != b'\0':
        byte_columns += current_byte
        

    columns       = byte_columns.decode("utf-8")
    columns_count = len(columns.split(","))
    
    body_line_binary_format = get_imu_values_type(columns_count)
    bytes_per_line          = struct.calcsize(body_line_binary_format)
    total_samples           = (os.path.getsize(imu_filepath) - imu_file.tell()) / bytes_per_line
    final_timestamp         = initial_timestamp + total_samples*delta_t
    
    if only_header:
        return (delta_t, initial_timestamp, columns)
    
    elif only_timestamp_range:
        return (initial_timestamp, final_timestamp)

    if isinstance(output, io.TextIOWrapper):
        output.write(columns + "\n")
    
    ########################
    # Read IMU file body:
    ########################

    # Parse timestamps to pointer positions in file:
    if timestamp_to is not None:
        timestamp_to = max(0, imu_file.tell() + bytes_per_line*math.floor((timestamp_to - initial_timestamp)/delta_t))


    if timestamp_from is not None and timestamp_from > initial_timestamp:
        timestamp_from = max(0, bytes_per_line*math.ceil((timestamp_from - initial_timestamp)/delta_t))
        imu_file.read(timestamp_from)
    
    if n_samples is not None:
        step = max(1, math.floor(total_samples / n_samples))
    
    # Skip offset lines:
    imu_file.read(offset*bytes_per_line)

    # Keep reading the file until it is finished or upper timestamp limit is reached, whatever happens first
    while (bdata := imu_file.read(bytes_per_line)) and (timestamp_to is None or imu_file.tell() < timestamp_to):
        values = struct.unpack(body_line_binary_format, bdata)
        
        if isinstance(output, list):
            output += [values]
            
        else:
            values = tuple(map(str, values))
            output.write(",".join(values) + "\n")

        # Skip step lines:
        imu_file.seek(imu_file.tell() + (step-1)*bytes_per_line)
        
    if isinstance(output, list):
        return output, delta_t, initial_timestamp, columns, step
    else:
        output.close()


def get_imu_header(delta_t, initial_timestamp, columns):
    """
    Encode data to write at the beginning of an IMU file.

    Args:
        delta_t (int): Timestamp increment between samples of the IMU file. Short int.
        initial_timestamp (int): Timestamp which correspond to the first sample in the IMU file. Long long int.
        columns (string): names of the columns of the original CSV excluding the timestamp column separated by commas. Lowercase ASCII characters utf-8 encoded

    Returns:
        bytes: bytes prepared to directly be writen in the IMU file.
        - 2 bytes for delta_t
        - 8 bytes for initial_timestamp
        - 1 bytes per character in columns.
    """
    header  = struct.pack(DELTA_T_TYPE, delta_t)
    header += struct.pack(INITIAL_TIMESTAMP_TYPE, initial_timestamp)
    header += struct.pack(get_imu_string_type(columns), columns)
    
    return header


def compute_tremor_amplitude(data, low_pass_freq, high_pass_freq, SFT):
    
    import numpy as np
    from scipy import signal
    
    # N: order of the filter
    # returns numerator and denominator of the polynomials of the IIR filterw
    b, a = signal.butter(N=4, Wn=[low_pass_freq, high_pass_freq], btype="bandpass", fs=SFT.fs)
    
    data = signal.filtfilt(b, a, data)

    data = SFT.spectrogram(data)
    
    # Parse to dB
    data = 10*np.log10(np.fmax(data, 1e-4))
    
    max_freq_index = np.argmax(data, axis=0)
    data = [data[row, col] for row, col in zip(max_freq_index, range(data.shape[1]))]
    
    frequencies = max_freq_index*SFT.delta_f
    
    return tuple(zip(frequencies, data))
    


def wtremor(imu_filepath, tremor_filepath, low_pass_freq, high_pass_freq, hop_seconds, window_seconds):

    from scipy import signal
    
    data, delta_t, initial_timestamp, columns, _ = rimu(imu_filepath)

    n_samples               = len(data)
    data                    = tuple(zip(*data)) # tranpose data matrix, each row has all the values for an axis now
    sampling_frequency      = (1/delta_t)*1000
    hop_size                = int(hop_seconds * sampling_frequency)
    window_size             = int(window_seconds*sampling_frequency)
    oversampling_factor     = 16
    mfft                    = 2**math.ceil(math.log(oversampling_factor * sampling_frequency, 2))
    gaussian_window         = signal.windows.gaussian(window_size, std=12, sym=True)
    SFT                     = signal.ShortTimeFFT(gaussian_window, hop=hop_size, fs=sampling_frequency, mfft=mfft, scale_to="psd")
    tremor_args             = (low_pass_freq, high_pass_freq, SFT)
    initial_t, final_t      = SFT.extent(n_samples)[:2]
    first_no_padding_sample = SFT.lower_border_end[1]
    last_no_padding_sample  = SFT.upper_border_begin(n_samples)[1]
    
    with multiprocessing.Pool(processes=len(columns.split(","))) as pool:
        data = pool.starmap(compute_tremor_amplitude, [(axis_data, *tremor_args) for axis_data in data])
        
    # Tranpose data again:
    data = tuple(zip(*data))
    # each row one value (frequency, amplitude) of each axis now
    
    # Header for the tremor file
    
    # delta_t of the spectrogram (Float)
    # initial_t of the spectrogram (can be negative due to pre-padding) (Float)
    # initial_timestamp (Long long unsigned int)
    # lower_border_end (Long long unsigned int)
    # upper_border_end (Long long unsigned int)
    
    header  = struct.pack(BIG_ENDIAN + FLOAT_32_BIT, SFT.delta_t)
    header += struct.pack(BIG_ENDIAN + FLOAT_32_BIT, initial_t)
    header += struct.pack(BIG_ENDIAN + UNSIGNED_LONG_LONG, initial_timestamp)
    header += struct.pack(BIG_ENDIAN + UNSIGNED_LONG_LONG, first_no_padding_sample)
    header += struct.pack(BIG_ENDIAN + UNSIGNED_LONG_LONG, last_no_padding_sample)
    header += struct.pack(BIG_ENDIAN + str(len(columns)) + STRING_8_BIT, columns.encode("utf-8") + b'\0')
    
    tremor_file = open(tremor_filepath, "wb")
    
    tremor_file.write(header)
    
    for row in data:
        for axis_values in row:
            tremor_line = struct.pack(BIG_ENDIAN + str(2) + FLOAT_32_BIT, *axis_values)
            tremor_file.write(tremor_line)

    
    tremor_file.close()
    
if __name__ == "__main__":
    
    import sys
    
    wtremor("/home/ging/netremor/imu-files/38ec605012c411ef99d08c1759ee1f3c-accelerometer.imu", "test.tr", 2, 10, 1, 3)
    sys.exit(0)
    
    import getopt
    
    def display_help(exit_code = 0):
        print("Exit code: %s" % exit_code)
        print("""Usage: python imu.py <options>
              
OPTIONS:

Required:
    -m (--mode): read|write
    -i (--input-file): input file path

Optional:    
    -o (--output-file): output file path (required for "write" mode)
    -d (--delta-timestamp): timestamp increment
    -t (--timestamp-threshold): timestamp maximum difference before splitting file (only for "write" mode)
    -n (--timestamp-name): timestamp column name
    -s (--separator): CSV separator character
    -h (--help)
""")
        sys.exit(exit_code)
        
    # Default formatting values:
    timestamp_colname   = "timestamp"
    delta_t             = 30
    separator           = ","
    timestamp_threshold = 200

    # Required arguments:
    input_filepath = output_filepath = mode = None
    
    
    # Determine input filepath, output filepath and what to do with the data with the command line arguments:
    argv = sys.argv[1:]
    
    try:
        opts, args = getopt.getopt(argv, "hm:i:o::d::t::n::s::", ["help", "mode=", "input-file=", "output-file", "delta-timestamp", "timestamp-threshold", "timestamp-name", "separator"])
    except getopt.GetoptError as e:
        display_help(-1)

        
    if len(opts) == 0:
        display_help(-1)

    for opt, arg in opts:
        
        if opt in ("-h", "--help"):
            display_help(0)
            
        elif opt in ("-i", "--input-file"):
            input_filepath = arg
            
        elif opt in ("-o", "--output-file"):
            output_filepath = arg

        elif opt in ("-m", "--mode"):
            
            if arg not in ("read", "write"):
                display_help(-1)
                
            mode = arg
                
        elif opt in ("-s", "--separator"):
            separator = arg
            
        elif opt in ("-n", "--timestamp-name"):
            timestamp_colname = arg
            
        elif opt in ("-d", "--delta-timestamp"):
            delta_t = int(arg)
            
        elif opt in ("-t", "--timestamp-threshold"):
            timestamp_threshold = int(arg)
                
        else:
            display_help(-1)
                
    
    # Check the module has been called properly (defined input file and, if in write mode, defined output file)
    if input_filepath is None or mode is None or (mode == "write" and output_filepath is None):
        display_help(-1)
    
            
    # Read the contents of a IMU-formatted file and output them into the specified output file
    if mode == "write":
        wimu(input_filepath, output_filepath, delta_t, timestamp_threshold, timestamp_colname, separator)
        
    # Format the data from a CSV file (input file) and write it into a IMU file (output file).
    elif mode == "read":
        rimu(input_filepath, output_filepath)