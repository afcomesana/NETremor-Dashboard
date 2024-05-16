# PYTHON LIBRARIES
import os
import re
import math
import uuid
import signal
import threading
import multiprocessing
import numpy as np
from csvsort import csvsort


# CUSTOM MODULES
import imu

# DJANGO FRAMEWORK
from endpoint.models import Subject, Task, Record, Datafile, Imufile, Datafile_task_rel
from django.conf import settings
from django.db.models import Min, Max
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError
from django.core.files.storage import default_storage

SENSOR_NAMES = list(map(lambda sensor: sensor[0], settings.SENSOR_CHOICES))

def save_tasks(incoming_tasks):
    """
    Save new tasks in the database.

    Args:
        incoming_tasks (Dict[]): Array with the tasks belonging to the record that has been sent.
        Each item will have at least the following three keys:
        - task_id
        - task_name
        - task_description
    """
    for task in incoming_tasks:
        if "task_id" in task.keys():
            task["task_id"] = task["task_id"].upper()
    
    # Create list with each item being the arguments for creating the task that is not yet in the database
    current_stored_tasks = Task.objects.values_list("id", flat=True).distinct()
    tasks_to_store       = list(map(lambda task: {
        "id": task["task_id"],
        "name": task["task_name"] if "task_name" in task.keys() else None,
        "description": task["task_description"] if "task_description" in task.keys() else None,
    }, filter(lambda incoming_task: "task_id" in incoming_task.keys() and incoming_task["task_id"] not in current_stored_tasks, incoming_tasks)))
    
    # Storing those tasks that do not exist in the database:
    [Task(**task).save() for task in tasks_to_store]

def save_subject(post_fields):
    # Save/update subject in database:
    if "subject_id" not in post_fields.keys():
        raise KeyError("Subject ID must be provided.")
    
    post_fields["id"] = post_fields["subject_id"]
    del post_fields["subject_id"]
    
    try:
        subject = Subject(**{field.name:post_fields[field.name] if field.name in post_fields else None for field in Subject._meta.fields})
        
        if subject.dominant_hand not in get_model_field_choices_keys(Subject.DOMINANT_HAND_CHOICES):
            subject.dominant_hand = None
            
        if subject.gender not in get_model_field_choices_keys(Subject.GENDER_CHOICES):
            subject.gender = None
            
        if isinstance(subject.diagnosis, str) and not subject.diagnosis.strip():
            subject.diagnosis = None 

        subject.save()
        
    except KeyError as e:
        raise KeyError("Missing field in incoming request %s" % e)
    
    return subject
    
def save_imufile(imu_filepath, datafile = None, record = None):
    initial_timestamp, final_timestamp = imu.rimu(imu_filepath, only_timestamp_range=True)
    
    imufile_args = {
        "name": os.path.basename(imu_filepath),
        "initial_timestamp": initial_timestamp,
        "final_timestamp": final_timestamp,
    }
    
    if isinstance(datafile, Datafile):
        imufile_args["datafile"] = datafile
        imufile_args["sensor"]   = datafile.sensor
        
    if isinstance(record, Record):
        imufile_args["record"] = record
    
    Imufile(**imufile_args).save()
    
def get_model_field_choices_keys(choices):
    """
    Get the keys of the choices of a Model class from Django.
    
    Args:
    - choices: list of tuples passed as argument to the choices parameter field definition

    Return:
    - list[str] the keys of the choices
    """
    return [choice[0] for choice in choices]


def process_record_datafiles(record):
    """
    1. Sort record datafiles.
    2. Format data to IMU file type.

    Args:
        record (Record): Record whose files are going to be parsed to IMU format.
    """
    
    datafiles = record.datafile_set.all()
    
    # 1. Sort record datafiles (by default the sort key is the "timestamp").
    # multiprocessing.Pool can't be used for this sorting process because the
    # process uses the multiprocessig itself and would raise an error
    # [sort_csv_file(datafile) for datafile in datafiles]
    
    
    # 2. Format data to IMU file type.
    pool = multiprocessing.Pool(processes=datafiles.count())
    
    csv_filepaths = tuple(map(lambda datafile: os.path.join(settings.DATAFILES_DIR, datafile.name), datafiles))
    imu_filepaths = tuple(map(lambda datafile: os.path.join(settings.IMUFILES_DIR, re.sub(r'\.csv$', ".imu", datafile.name)), datafiles))
    wimu_args     = tuple(map(lambda datafile: (datafile.delta_t, datafile.timestamp_threshold, datafile.timestamp_colname, datafile.separator), datafiles))
    wimu_args     = tuple(map(lambda filepaths, args: filepaths + args, zip(csv_filepaths, imu_filepaths), wimu_args))
    
    imu_filepaths = pool.starmap(imu.wimu, wimu_args)

    for datafile, imufiles in zip(datafiles, imu_filepaths):
        
        # Save IMU files in the database.
        [save_imufile(imufile, datafile, record) for imufile in imufiles]
        
        # Update null values of the datafile in the database.
        initial_timestamp, final_timestamp = datafile.imufile_set.aggregate(Min("initial_timestamp"), Max("final_timestamp")).values()
        datafile.is_processed              = True
        datafile.initial_timestamp         = initial_timestamp
        datafile.final_timestamp           = final_timestamp
        datafile.save()

    # Compute tremor files from imufiles
    # [write_tremor_file(imufile) record.imufile_set.all()]
    
    
def bandpass_filter(data, low_pass_frequency, high_pass_frequency, sampling_frequency):
    # N: order of the filter
    # returns numerator and denominator of the polynomials of the IIR filterw
    b, a = signal.butter(N=4, Wn=[low_pass_frequency, high_pass_frequency], btype="bandpass", fs=sampling_frequency)

    return signal.filtfilt(b, a, data)

def write_tremor_file(imufile):
    # 1. Read imu file
    # 2. Rearrange output tuple to get all the axis values in the same tuple
    # 3. Compute parallelwise each axis tremor values
    
    LOW_PASS_FREQ  = 2 # Herz
    HIGH_PASS_FREQ = 10 # Herz
    
    delta_t = imufile.datafile.delta_t
    
    if not delta_t:
        delta_t = settings.DEFAULT_DELTA_T
    
    sampling_frequency = 1/delta_t
    
    
    imu_filepath = os.path.join(settings.IMUFILES_DIR, imufile.name)
    
    data = tuple(zip(*imu.rimu(imu_filepath)))
    
    n_axis = len(data)
    bandpass_filter_args = (LOW_PASS_FREQ, HIGH_PASS_FREQ, sampling_frequency)
    
    with multiprocessing.Pool(processes=len(data)) as pool:
        data = pool.starmap(bandpass_filter, [(axis_data, *bandpass_filter_args) for axis_data in data])
    
    axis_data = bandpass_filter(axis_data, LOW_PASS_FREQ, HIGH_PASS_FREQ, sampling_frequency)
    hop_seconds = 1
    hop_samples = int(hop_seconds * sampling_frequency)
    
    window_seconds = 3
    window_size = int(3*sampling_frequency)
    oversampling_factor = 16
    
    mfft = 2**math.ceil(math.log(oversampling_factor * sampling_frequency, 2))
    
    gaussian_window = signal.windows.gaussian(window_size, std=12, sym=True)
    
    SFT = signal.ShortTimeFFT(gaussian_window, hop=hop_samples, fs=sampling_frequency, mfft=mfft, scale_to="psd")
    axis_data = 10*np.log10(np.fmax(SFT.spectrogram(axis_data), 1e-4))
    
    
    
def sort_csv_file(datafile, key = "timestamp", separator = ","):
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
        
        keys = list(map(lambda colname: colname.strip(), file.readline().split(separator)))
        try:
            key_index = keys.index(key)
            
        # Key is not part of the columns:
        except ValueError:
            # File won't be sorted.
            return
    
    # Sort the file:
    csvsort(datafile_path, [key_index], delimiter=separator)
    

def save_ambulatory_record(request, subject, recorded_tasks, record_added_on):
    
    # Create and attach record to the subject:
    record = Record(subject = subject, type="ambulatory", added_on=record_added_on)
    record.save()
    
    # Save raw data files and corresponding tasks:
    for task in recorded_tasks:
        
        # task will be a dictionary with information about the task
        # description, task_id, task_name, files corresponding to
        # each sensor, and so on
        
        for sensor in SENSOR_NAMES:
            try:
                # Store the file in the data files directory:
                file      = request.FILES[task["%s_filename" % sensor]]
                filepath  = os.path.join(settings.DATAFILES_DIR, file.name)
                
                if os.path.exists(filepath):
                    print("File", file.name, "already exists. Data not saved.")
                    continue
                
                default_storage.save(filepath, file)
                
                # TODO: Add necessary fields to IMU encoding
                datafile = Datafile(record=record, name=file.name, sensor=sensor)
                datafile.save()
                
                # Store the relation between the task, the record and the datafile:
                if "task_id" in task.keys():
                    Datafile_task_rel(record=record, datafile=datafile, task_id=task["task_id"], trial=task["trial"]).save()                    
                
            except KeyError:
                print("Current task doesn't have %s file" % sensor)
                continue
        

    if record.datafile_set.count() == 0:
        record.delete()
        return HttpResponseBadRequest("This record is already saved.")
    
    # Process stored data without blocking the response to the request
    threading.Thread(target=process_record_datafiles, args=[record]).start()
    
    return HttpResponse("OK")

def save_continuous_record(request, subject, recorded_tasks, record_added_on, delta_t):
    # Create or retrieves record:
    record, _ = subject.record_set.get_or_create(type="continuous", defaults={"added_on": record_added_on})
    
    try:
        for file in request.FILES:

            # Do not save files whose sensor could not be identified:
            sensor = next(filter(lambda sensor_name: sensor_name in file, SENSOR_NAMES), None)
            if sensor is None:
                print("Skipping not recognized sensor file: %s." % file)
                continue
            
            # Create database instance and insert file:
            filename = re.sub(r'\.(dat|txt)$', ".csv", file)
            
            # Prevent overwriting existing files
            # TODO: Check if the first timestamp is the same to avoid repeating data
            if os.path.exists(os.path.join(settings.DATAFILES_DIR, filename)):
                filename, extension = filename.split(".")
                filename = "%s-%s.%s" % (filename, uuid.uuid1().hex, extension)
            
            
            print("Saving data file with delta_t:", delta_t)
            # Store data file instance in database:
            datafile_args = {
                "record": record,
                "name": filename,
                "sensor": sensor,
                
                # TODO: Send this arguments in the request
                "delta_t": delta_t,
                "timestamp_threshold": 200,
                "timestamp_colname": "timestamp",
                "separator": ",",
            }
            
            datafile = Datafile(**datafile_args)
            datafile.save()
            
            # Save tasks recorded in continuous record:
            for task in recorded_tasks:
                Datafile_task_rel(record=record, datafile=datafile, task_id=task["task_id"], starts_at=task["starts_at"], ends_at=task["ends_at"],).save()

            filepath = os.path.join(settings.DATAFILES_DIR, datafile.name)
            default_storage.save(filepath, request.FILES[file])
            
    except Exception as e:
        print("Error during continuous record saving process:", e)
        return HttpResponseServerError("Unexpected error in server.")
        
    # TODO: Throw handle new datafiles process
    threading.Thread(target = process_record_datafiles, args = [record]).start()
    
    return HttpResponse(200)