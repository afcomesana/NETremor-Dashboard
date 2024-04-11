# PYTHON LIBRARIES
import os
import multiprocessing
from csvsort import csvsort

# DJANGO FRAMEWORK
from endpoint.models import Subject
from django.conf import settings



def save_subject(post_fields):
    # Save/update subject in database:
    if "subject_id" not in post_fields.keys():
        raise KeyError("Subject ID must be provided.")
    
    post_fields["id"] = post_fields["subject_id"]
    del post_fields["subject_id"]
    
    try:
        subject = Subject(
            **{
                field.name:
                    post_fields[field.name] if field.name in post_fields else None for field in Subject._meta.fields
            }
        )
        
        if subject.dominant_hand not in get_choices_keys(Subject.DOMINANT_HAND_CHOICES):
            subject.dominant_hand = None
            
        if subject.gender not in get_choices_keys(Subject.GENDER_CHOICES):
            subject.gender = None
            
        if isinstance(subject.diagnosis, str) and not subject.diagnosis.strip():
            subject.diagnosis = None 

        subject.save()
        
    except KeyError as e:
        raise KeyError("Missing field in incoming request %s" % e)
    
    return subject
    
    
def get_choices_keys(choices):
    """
    Get the keys of the choices of a Model class from Django.
    
    Args:
    - choices: list of tuples passed as argument to the choices parameter field definition

    Return:
    - list[str] the keys of the choices
    """
    return list(map(lambda choice: choice[0], choices))

def process_record_data(record):
    """
    Applies the computations required to extract the information from the raw datafile.
    
    1. Sort the data of each datafile in the record according to its timestamps.
    2. a. Compute spectrogram
    2. b. Apply bradykinetics computations.
    2. c. Apply daily life activities.

    Args:
        record (Record): record whose data is going to be processed.
    """
    
    # Create pool to carry out parallelized computations:
    pool = multiprocessing.Pool()
    
    # 1. Sort the data of each datafile in the record according to its timestamps.
    pool.map(sort_csv_file, list(zip(record.datafile_set.all(), ["timestamp"]*record.datafile_set.count())))
    
    # TODO: Make sure data does not need to be interpolated.
    
def sort_csv_file(datafile, key, separator = ","):
    """
    Sort a CSV file according given a column key.

    Args:
        datafile (Datafile): instance of the Datafile class with info about raw sensor data.
        key (string): column which will be used to sort the file.
        separator (string): string used in the CSV file to define the columns (default is ",").
    """
    
    # Define the actual path of the datafile:
    datafile_path = os.path.join(settings.DATAFILES_DIR, datafile.name)

    # Find the column index of the key used to sort:
    with open(datafile_path, "r") as file:
        keys = file.readline().split(separator)
        
        try:
            key_index = keys.index(key)
            
        # Key is not part of the columns:
        except ValueError:
            # File won't be sorted.
            return
    
    # Sort the file:
    csvsort(datafile_path, [key_index], delimiter=separator)