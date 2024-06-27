import os
import io
import math
import string
import struct
from typing import NamedTuple

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


# IMU AND TREMOR FILE TYPES:
class FormatedValue(NamedTuple):
    name: str
    binary_format: str
    bytes_per_value: int

IMU_DELTA_T_TYPE               = FormatedValue("delta_t", BIG_ENDIAN + UNSIGNED_SHORT_INT, BYTES_PER_UNSIGNED_SHORT_INT)
IMU_INITIAL_TIMESTAMP_TYPE     = FormatedValue("initial_timestamp", BIG_ENDIAN + UNSIGNED_LONG_LONG, BYTES_PER_UNSIGNED_LONG_LONG)
TREMOR_DELTA_T_TYPE            = FormatedValue("delta_t", BIG_ENDIAN + FLOAT_32_BIT, BYTES_PER_FLOAT_32_BIT)
TREMOR_INITIAL_T_TYPE          = FormatedValue("initial_t", BIG_ENDIAN + FLOAT_32_BIT, BYTES_PER_FLOAT_32_BIT)
TREMOR_INITIAL_TIMESTAMP_TYPE  = FormatedValue("initial_timestamp", BIG_ENDIAN + UNSIGNED_LONG_LONG, BYTES_PER_UNSIGNED_LONG_LONG)
TREMOR_FIRST_NO_PADDING_SAMPLE = FormatedValue("first_no_padding_sample", BIG_ENDIAN + UNSIGNED_LONG_LONG, BYTES_PER_UNSIGNED_LONG_LONG)
TREMOR_LAST_NO_PADDING_SAMPLE  = FormatedValue("last_no_padding_sample", BIG_ENDIAN + UNSIGNED_LONG_LONG, BYTES_PER_UNSIGNED_LONG_LONG)

def get_header_string_type(text):
    return BIG_ENDIAN + str(len(text)) + STRING_8_BIT

def get_body_sample_format(columns_count, encoding = FLOAT_32_BIT):
    return BIG_ENDIAN + str(columns_count) + encoding

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
    columns = [col.strip() for col in columns]

    try:
        timestamp_index = columns.index(timestamp_colname)
        
    except ValueError:
        raise NameError("Timestamp column name not in file header.")

    columns.remove(timestamp_colname)
    
    # This will be used for parsing values in the body of the file
    body_line_binary_format = get_body_sample_format(len(columns))
    
    columns = list(map(lambda col: "".join(filter(lambda char: char in string.ascii_lowercase, col.lower())), columns))
    columns = separator.join(columns).encode("utf-8") + b'\0'
    
    # Get first timestamp to store it in IMU file header:
    initial_timestamp = int(csv_file.readline().split(separator)[timestamp_index].strip())
    
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
    
    header_fields = [
        IMU_DELTA_T_TYPE,
        IMU_INITIAL_TIMESTAMP_TYPE
    ]
    
    return read_custom_formatted_file(imu_filepath, header_fields, output_filepath, timestamp_from, timestamp_to, step, offset, n_samples, only_header, only_timestamp_range)
    

def rtremor(tremor_filepath, output_filepath = None, timestamp_from = None, timestamp_to = None, step = 1, offset = 0, n_samples = None, only_header = False, only_timestamp_range = False):
        
    # delta_t of the spectrogram (Float)
    # initial_t of the spectrogram (can be negative due to pre-padding) (Float)
    # initial_timestamp (Long long unsigned int)
    # first_no_padding_sample (Long long unsigned int)
    # last_no_padding_sample (Long long unsigned int)
        
    header_fields = [
        TREMOR_DELTA_T_TYPE,
        TREMOR_INITIAL_T_TYPE,
        TREMOR_INITIAL_TIMESTAMP_TYPE,
        TREMOR_FIRST_NO_PADDING_SAMPLE,
        TREMOR_LAST_NO_PADDING_SAMPLE,   
    ]
            
    return read_custom_formatted_file(tremor_filepath, header_fields, output_filepath, timestamp_from, timestamp_to, step, offset, n_samples, only_header, only_timestamp_range)

def read_custom_formatted_file(formatted_filepath, header_fields, output_filepath = None, timestamp_from = None, timestamp_to = None, step = 1, offset = 0, n_samples = None, only_header = False, only_timestamp_range = False):
    
    formatted_file = open(formatted_filepath, "rb")
    output = []
    if output_filepath is not None:
        output = open(output_filepath, "w")

    ##############################
    # Read formatted file header:
    ##############################
    header = {field.name: struct.unpack(field.binary_format, formatted_file.read(field.bytes_per_value))[0] for field in header_fields}
    header["columns"] = read_header_string_field(formatted_file)
    
    if only_header:
        return header
    
    body_line_binary_format = get_body_sample_format(len(header["columns"].split(",")))
    bytes_per_line          = struct.calcsize(body_line_binary_format)
    total_samples           = (os.path.getsize(formatted_filepath) - formatted_file.tell()) / bytes_per_line
    final_timestamp         = header["initial_timestamp"] + int(total_samples*header["delta_t"])
        
    if only_timestamp_range:
        return (header["initial_timestamp"], final_timestamp)

    if isinstance(output, io.TextIOWrapper):
        output.write(header["columns"] + "\n")
    
    ############################
    # Read formatted file body:
    ############################
    
    timestamp_from = max(header["initial_timestamp"], timestamp_from or header["initial_timestamp"])
    timestamp_to   = min(final_timestamp, timestamp_to or final_timestamp)
    
    if n_samples is not None:
        samples_in_time_range = (timestamp_to - timestamp_from)/(header["delta_t"])
        step = max(1, math.floor(samples_in_time_range / n_samples))
        
    # Parse timestamps to pointer positions in file:
    timestamp_to   = max(0, formatted_file.tell() + bytes_per_line*math.floor((timestamp_to - header["initial_timestamp"])/(header["delta_t"])))
    timestamp_from = max(0, bytes_per_line*math.ceil((timestamp_from - header["initial_timestamp"])/(header["delta_t"])))
    formatted_file.read(timestamp_from)
    
    # Skip offset lines:
    formatted_file.read(offset*bytes_per_line)

    # Keep reading the file until it is finished or upper timestamp limit is reached, whatever happens first
    while (bdata := formatted_file.read(bytes_per_line)) and (timestamp_to is None or formatted_file.tell() < timestamp_to):
        values = struct.unpack(body_line_binary_format, bdata)
        
        if isinstance(output, list):
            output += [values]
            
        else:
            values = tuple(map(str, values))
            output.write(",".join(values) + "\n")

        # Skip step lines:
        formatted_file.seek(formatted_file.tell() + (step-1)*bytes_per_line)
        
    if isinstance(output, list):
        return output, header, step
    
    else:
        # TODO: Add timestamp column to CSV file
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
    header  = struct.pack(IMU_DELTA_T_TYPE.binary_format, delta_t)
    header += struct.pack(IMU_INITIAL_TIMESTAMP_TYPE.binary_format, initial_timestamp)
    header += struct.pack(get_header_string_type(columns), columns)
    
    return header

def compute_tremor_amplitude(data, low_pass_freq, high_pass_freq, SFT):
    
    import numpy as np
    from scipy import signal
    
    # N: order of the filter
    # returns numerator and denominator of the polynomials of the IIR filterw
    b, a = signal.butter(N=4, Wn=[low_pass_freq, high_pass_freq], btype="bandpass", fs=SFT.fs)
    
    data = signal.filtfilt(b, a, data)
    
    try:
        data = SFT.spectrogram(data)
        
    except ValueError as e:
        print("Could not compute tremor with", len(data), "samples", e)
        return []
    
    # Parse to dB
    
    max_freq_index = np.argmax(data, axis=0)
    data = [data[row, col] for row, col in zip(max_freq_index, range(data.shape[1]))]
    
    frequencies = max_freq_index*SFT.delta_f
    
    return tuple(zip(frequencies, data))
    

def read_header_string_field(file):
    field = b''
    while (char := file.read(BYTES_PER_CHAR_8_BIT)) != b'\0':
        field += char
        
    return field.decode("utf-8")

def wtremor(imu_filepath, tremor_filepath, low_pass_freq, high_pass_freq, hop_seconds, window_seconds):
    
    from scipy import signal
    
    data, imu_header, _ = rimu(imu_filepath)
    n_samples           = len(data)
    data                = tuple(zip(*data)) # tranpose data matrix, each row has all the values for an axis now
    sampling_frequency  = (1/imu_header["delta_t"])*1000
    hop_size            = int(hop_seconds * sampling_frequency)
    window_size         = int(window_seconds*sampling_frequency)
    
    if n_samples < window_size / 2:
        return
    
    oversampling_factor     = 16
    mfft                    = 2**math.ceil(math.log(oversampling_factor * sampling_frequency, 2))
    gaussian_window         = signal.windows.gaussian(window_size, std=12, sym=True)
    SFT                     = signal.ShortTimeFFT(gaussian_window, hop=hop_size, fs=sampling_frequency, mfft=mfft, scale_to="psd")
    initial_t, _            = SFT.extent(n_samples)[:2]
    first_no_padding_sample = SFT.lower_border_end[1]
    last_no_padding_sample  = SFT.upper_border_begin(n_samples)[1]
    tremor_columns          = ",".join(["%s_frequency,%s_amplitude" % (col, col) for col in imu_header["columns"].split(",")]).encode("utf-8") + b'\0'
    
    data = tuple(compute_tremor_amplitude(axis_data, low_pass_freq, high_pass_freq, SFT) for axis_data in data)

    # Tranpose data again:
    data = tuple(zip(*data))

    # Add or substract (most probably substract) the initial time of the computed tremor amplitude.
    initial_timestamp = int(imu_header["initial_timestamp"] + initial_t*1000)

    # Header for the tremor file
    
    # delta_t of the spectrogram (Float)
    # initial_t of the spectrogram (can be negative due to pre-padding) (Float)
    # initial_timestamp (Long long unsigned int)
    # first_no_padding_sample (Long long unsigned int)
    # last_no_padding_sample (Long long unsigned int)
    
    header  = struct.pack(TREMOR_DELTA_T_TYPE.binary_format, SFT.delta_t*1000)
    header += struct.pack(TREMOR_INITIAL_T_TYPE.binary_format, initial_t)
    header += struct.pack(TREMOR_INITIAL_TIMESTAMP_TYPE.binary_format, initial_timestamp)
    header += struct.pack(TREMOR_FIRST_NO_PADDING_SAMPLE.binary_format, first_no_padding_sample)
    header += struct.pack(TREMOR_LAST_NO_PADDING_SAMPLE.binary_format, last_no_padding_sample)
    header += struct.pack(get_header_string_type(tremor_columns), tremor_columns)
    
    # Each sample will consist on a value for the frequency and another for amplitude (2 fields)
    body_line_binary_format = get_body_sample_format(2)
    
    with open(tremor_filepath, "wb") as tremor_file:
    
        tremor_file.write(header)
        
        for row in data:
            for axis_values in row:
                tremor_line = struct.pack(body_line_binary_format, *axis_values)
                tremor_file.write(tremor_line)
                
    return tremor_filepath
    
if __name__ == "__main__":
    
    import sys
    
    # wtremor("/home/ging/netremor/imu-files/5b478e8f1da611efb3248c1759ee1f3c-accelerometer.imu", "test.tr", 2, 10, 1, 3)
    # print("Tremor file written")
    # data, header = rtremor("/home/ging/netremor/tremor-files/1ef9f15116ac11efbd148c1759ee1f3c-accelerometer.tr")
    # print(data[:5])
    # print(header)
    
    # sys.exit(0)
    
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