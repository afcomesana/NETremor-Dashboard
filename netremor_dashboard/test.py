import os

datafiles_dir = "/home/ging/netremor/data-files"
filename = "2f73366bc5765cb9bdc1c7f436d03067f200958ff5e7a95635b5577815b62e96-1718628117678-gyroscope.csv"


def sort_csv_file(datafile_path, key = "timestamp", separator = ","):
    """
    Sort a CSV file according given a column key.

    Args:
        datafile (Datafile): instance of the Datafile class with info about raw sensor data.
        key (string): column which will be used to sort the file.
        separator (string): string used in the CSV file to define the columns (default is ",").
    """
    
    # Define the actual path of the datafile:
    # datafile_path = os.path.join(settings.DATAFILES_DIR, datafile.name)
    
    tmp_filename = "tmp_%s" % os.path.basename(datafile_path)
    tmp_filepath = os.path.join(os.path.dirname(datafile_path), tmp_filename)
    
    # Find the column index of the key used to sort:
    with open(datafile_path, "r") as original_file:
        
        column_names = original_file.readline()
        keys         = list(map(lambda colname: colname.strip(), column_names.split(separator)))
        
        try:
            key_index = keys.index(key)
            
        # Key is not part of the columns:
        except ValueError:
            # File won't be sorted.
            return
        
        with open(tmp_filepath, "w") as temporary_file:
            
            while line := original_file.readline():
                temporary_file.write(line)
    
    key_index += 1
    
    
    # Sort the file:
    os.system("sort -n -t '%s' -k %s,%s -o %s %s" % (separator, key_index, key_index, tmp_filepath, tmp_filepath))
    
    with open(tmp_filepath, "r") as sorted_file:
        
        with open(datafile_path, "w") as file:
            file.write(column_names)

            while line := sorted_file.readline():
                file.write(line)
                
    os.unlink(tmp_filepath)


sort_csv_file(os.path.join(datafiles_dir, filename))