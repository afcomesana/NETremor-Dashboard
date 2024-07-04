# PYTHON LIBRARIES
import os
import re
import threading
import statistics
import multiprocessing
import pandas as pd
import numpy as np
from scipy import signal


# CUSTOM MODULES
import imu
import utils

# DJANGO FRAMEWORK
from endpoint.models import Subject, Task, Position, Record, Datafile, Imufile, Tremor_file, Datafile_task_rel, Datafile_position_rel, Bradykinesia
from django.conf import settings
from django.db.models import Min, Max
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError
from django.core.files.storage import default_storage

SENSOR_NAMES = list(map(lambda sensor: sensor[0], settings.SENSOR_CHOICES))
LOGGING_KEY  = "endpoint"

def save_tasks_or_positions(incoming_tasks_or_positions, item_type):
    """
    Save new tasks or positions in the database.

    Args:
        incoming_tasks_or_positions (Dict[]): Array with the tasks or positions belonging to the record that has been sent.
        Each item will have at least the following three keys:
        - task_id          | position_id
        - task_name        | position_name
        - task_description | position_description
    """
    
    if item_type not in ("task", "position"):
        raise "Unknown item type to store in database. Must be 'task' or 'position'."
    
    item_id_key          = "%s_id" % item_type
    item_name_key        = "%s_name" % item_type
    item_description_key = "%s_description" % item_type
    item_class           = Task if item_type == "task" else Position
    
    incoming_tasks_or_positions = [item for item in incoming_tasks_or_positions if item_id_key in item.keys()]
    
    for item in incoming_tasks_or_positions:
        item[item_id_key] = item[item_id_key].upper()
    
    # Create list with each item being the arguments for creating the task that is not yet in the database
    current_stored_tasks = item_class.objects.values_list("id", flat=True).distinct()
    items_to_store       = list(map(lambda item: {
        "id": item[item_id_key],
        "name": item[item_name_key] if item_name_key in item.keys() else None,
        "description": item[item_description_key] if item_description_key in item.keys() else None,
    }, filter(lambda incoming_task: item_id_key in incoming_task.keys() and incoming_task[item_id_key] not in current_stored_tasks, incoming_tasks_or_positions)))

    
    # Storing those items that do not exist in the database:
    [item_class(**item).save() for item in items_to_store]


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
    
def save_processed_file(filepath, read_file_callback, filetype_data_class, datafile = None, record = None):
    
    initial_timestamp, final_timestamp = read_file_callback(filepath, only_timestamp_range=True)
    
    args = {
        "name": os.path.basename(filepath),
        "initial_timestamp": initial_timestamp,
        "final_timestamp": final_timestamp,
    }
    
    if isinstance(datafile, Datafile):
        args["datafile"] = datafile
        args["sensor"]   = datafile.sensor
        
    if isinstance(record, Record):
        args["record"] = record
    
    filetype_data_class(**args).save()
    
    
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
    3. Compute tremor on IMU files.

    Args:
        record (Record): Record whose files are going to be parsed to IMU format.
    """
    
    if record.is_being_processed:
        return
    
    record.is_being_processed = True
    record.save()
    
    datafiles = record.datafile_set.filter(is_processed=False)
    
    try:
        with multiprocessing.Pool() as pool:
            
            # 1. Sort record datafiles (by default the sort key is the "timestamp").
            # multiprocessing.Pool can't be used for this sorting process because the
            # process uses the multiprocessig itself and would raise an error
            pool.map(sort_csv_file, datafiles)
            
            threading.Thread(compute_bradykinesia, args=[record.subject_id]).start()
            
            # 2. Format data to IMU file type.        
            csv_filepaths = tuple(os.path.join(settings.DATAFILES_DIR, datafile.name) for datafile in datafiles)
            imu_filepaths = tuple(os.path.join(settings.IMUFILES_DIR, re.sub(r'\.csv$', ".imu", datafile.name)) for datafile in datafiles)
            wimu_args     = tuple((datafile.delta_t, datafile.timestamp_threshold, datafile.timestamp_colname, datafile.separator) for datafile in datafiles)
            wimu_args     = tuple(map(lambda filepaths, args: filepaths + args, zip(csv_filepaths, imu_filepaths), wimu_args))
            
            imu_filepaths = pool.starmap(imu.wimu, wimu_args)
            
            # Save IMU file instances in database:
            for datafile, imufiles in zip(datafiles, imu_filepaths):
                
                # Save IMU files in the database.
                [save_processed_file(imufile, imu.rimu, Imufile, datafile, record) for imufile in imufiles]
                
                # Update null values of the datafile in the database.
                initial_timestamp, final_timestamp = datafile.imufile_set.aggregate(Min("initial_timestamp"), Max("final_timestamp")).values()
                datafile.initial_timestamp         = initial_timestamp
                datafile.final_timestamp           = final_timestamp
                datafile.save()
            
            imufiles           = record.imufile_set.all()
            tremor_filepaths   = tuple(os.path.join(settings.TREMOR_FILES_DIR, re.sub(r'\.imu$', '.tr', imufile.name)) for imufile in imufiles)
            tremor_files_count = imufiles.count()
            
            # 3. Compute tremor for each imufile and save computation in a "tremor" file
            tremor_filepaths = pool.starmap(
                imu.wtremor,
                zip(
                    tuple(os.path.join(settings.IMUFILES_DIR, imufile.name) for imufile in imufiles),
                    tremor_filepaths,
                    (settings.DEFAULT_TREMOR_LOW_PASS_FREQ,)*tremor_files_count,
                    (settings.DEFAULT_TREMOR_HIGH_PASS_FREQ,)*tremor_files_count,
                    (settings.DEFAULT_TREMOR_HOP_SECONDS,)*tremor_files_count,
                    (settings.DEFAULT_TREMOR_WINDOW_SECONDS,)*tremor_files_count,
                )
            )
            
            imufiles = [imufile for imufile, tremor_filepath in zip(imufiles, tremor_filepaths) if tremor_filepath is not None]
            tremor_filepaths = [tremor_filepath for tremor_filepath in tremor_filepaths if tremor_filepath is not None]
            
            # Once tremor is computed, save tremor files in database
            pool.starmap(
                save_processed_file,
                zip(
                    tremor_filepaths,
                    (imu.rtremor,)*tremor_files_count,
                    (Tremor_file,)*tremor_files_count,
                    tuple(imufile.datafile for imufile in imufiles),
                    (record,)*tremor_files_count
                )
            )

            
        for datafile in datafiles:
            datafile.is_processed = True
            datafile.save()
            
    except Exception as e:
        utils.write_log("Could not process record: %s" % repr(e), LOGGING_KEY, settings.LOG_ERROR)
        
    finally:
        record.is_being_processed = False
        record.save()
    
    
def bandpass_filter(data, low_pass_frequency, high_pass_frequency, sampling_frequency):
    # N: order of the filter
    # returns numerator and denominator of the polynomials of the IIR filterw
    b, a = signal.butter(N=4, Wn=[low_pass_frequency, high_pass_frequency], btype="bandpass", fs=sampling_frequency)

    return signal.filtfilt(b, a, data)
    
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
    
    tmp_filename  = "tmp_%s" % os.path.basename(datafile_path)
    tmp_filepath  = os.path.join(os.path.dirname(datafile_path), tmp_filename)
    
    # Find the column index of the key used to sort and write the temporary file without column names to order it:
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

def save_continuous_record(request, subject, recorded_tasks, recorded_positions, record_added_on, delta_t):
    # Create or retrieves record:
    record, _ = subject.record_set.get_or_create(type="continuous", defaults={"added_on": record_added_on})
    
    for file in request.FILES:
        # Do not save files whose sensor could not be identified:
        sensor = next(filter(lambda sensor_name: sensor_name in file, SENSOR_NAMES), None)
        if sensor is None:
            print("Skipping not recognized sensor file: %s." % file)
            continue
        
        # Create database instance and insert file:
        filename = re.sub(r'\.(dat|txt)$', ".csv", file)
        
        # Prevent overwriting existing files
        if os.path.exists(os.path.join(settings.DATAFILES_DIR, filename)):
            utils.write_log("Not saving file because it already exist %s" % filename, LOGGING_KEY, settings.LOG_WARN)
            continue
        
        filepath = os.path.join(settings.DATAFILES_DIR, filename)
        
        try:
            default_storage.save(filepath, request.FILES[file])
            
        except Exception as e:
            utils.write_log("Could not save continuous record file %s. - %s" % (file.name, repr(e)), LOGGING_KEY, settings.LOG_ERROR)
            return HttpResponseServerError("Unexpected error in server.")
    
    
        ##########################################        
        # Avoid storing duplicated sensor samples
        ##########################################
                
        try:
            with open(filepath, "r") as saved_file:
                saved_file.seek(0)
                columns          = [colname.strip() for colname in saved_file.readline().split(",")]
                timestamp_column = columns.index("timestamp")
                tmp_timestamp = saved_file.readline().split(",")[timestamp_column]
                first_timestamp  = int(tmp_timestamp)
                
        except Exception as e:
            return HttpResponseServerError("Could not get first timestamp from file: %s" % repr(e))

        overlap_datafiles = record.datafile_set.filter(sensor = sensor, final_timestamp__gt = first_timestamp).order_by("initial_timestamp")
        
        if len(overlap_datafiles) > 0:
            
            no_overlap_filename, extension = filename.split(".")
            no_overlap_filename = no_overlap_filename + "-no-overlap." + extension
            no_overlap_filepath = os.path.join(settings.DATAFILES_DIR, no_overlap_filename)

            with open(filepath, "r") as overlap_file:
                
                with open(no_overlap_filepath, "w") as no_overlap_file:
                    
                    # Write column names line
                    no_overlap_file.write(overlap_file.readline())
                    
                    # Process below is under the assumption that there are no overlapped files stored yet:
                    for overlap_datafile in overlap_datafiles:
                        
                        while line := overlap_file.readline():
                        
                            timestamp = int(line.split(",")[timestamp_column])
                            
                            if timestamp < overlap_datafile.initial_timestamp or timestamp > overlap_datafile.final_timestamp:
                                no_overlap_file.write(line)
                                
        
            os.unlink(filepath)
            os.rename(no_overlap_filepath, filepath)
            
            
        ##############################################
        # SAVE FILES, POSITIONS AND TASKS IN DATABASE
        ##############################################

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
        
        # Save tasks and position recorded in continuous record:
        for items, item_name, data_class in zip([recorded_tasks, recorded_positions], ["task", "position"], [Datafile_task_rel, Datafile_position_rel]):
            
            keys           = ["%s_id" % item_name, "starts_at", "ends_at"]
            items_to_store = [dict((key, item[key]) for key in keys if key in item.keys()) for item in items]

            [data_class(record=record, datafile=datafile, **item).save() for item in items_to_store]


    threading.Thread(target = process_record_datafiles, args = [record]).start()
    
    return HttpResponse(200)

def compute_bradykinesia(id_participant):
    print("Running compute bradykinesia with subject id", id_participant)
    
    # Verificación del participante
    if not id_participant: return
    
    # Definición de los parámetros de los filtros
    fs = 30.0
    frecuencia_corte_HP = 0.05
    frecuencia_corte_LP = 3.5
    lim_inf_brad = 0.1
    lim_sup_brad = 0.15
    frecuencia_corte_HP_norm = frecuencia_corte_HP / (0.5 * fs)
    frecuencia_corte_LP_norm = frecuencia_corte_LP / (0.5 * fs)
    b, a = signal.butter(N=4, Wn=frecuencia_corte_HP_norm, btype='high', analog=False)
    d, c = signal.butter(N=4, Wn=frecuencia_corte_LP_norm, btype='low', analog=False)

    
    records = Record.objects.filter(subject_id=id_participant)

    continuous_records = list(filter(lambda record: record.type == "continuous", records))
    ambulatory_records = list(filter(lambda record: record.type == "ambulatory", records))
    
    continuous_record_ids = [record.id for record in continuous_records]
    ambulatory_record_ids = [record.id for record in ambulatory_records]
    
    continuous_datafiles    = Datafile.objects.filter(record_id__in=continuous_record_ids, sensor="accelerometer")
    ambulatory_datafile_ids = [rel.datafile.id for rel in Datafile_task_rel.objects.filter(record_id__in=ambulatory_record_ids, task__isnull=False)]
    ambulatory_datafiles    = Datafile.objects.filter(id__in=ambulatory_datafile_ids, sensor="accelerometer")
    
    nombres  = [datafile.name for datafile in continuous_datafiles]
    nombres += [datafile.name for datafile in ambulatory_datafiles]

    if nombres:
        potMax = []
        frecDom = []

        for nombre in nombres:

            # Leer el archivo CSV y mostrar su contenido
            file_path = os.path.join(settings.DATAFILES_DIR, nombre)
            if os.path.isfile(file_path):
                datos = pd.read_csv(file_path)

                # Limpiar nombres de columnas
                datos.columns = datos.columns.str.strip()

                if 'x' in datos.columns and 'y' in datos.columns and 'z' in datos.columns:
                    aceleracion_x = datos['x']
                    aceleracion_y = datos['y']
                    aceleracion_z = datos['z']

                    aceleracion_x_filtrada_HP = signal.filtfilt(b, a, aceleracion_x)
                    aceleracion_y_filtrada_HP = signal.filtfilt(b, a, aceleracion_y)
                    aceleracion_z_filtrada_HP = signal.filtfilt(b, a, aceleracion_z)

                    aceleracion_x_filtrada_LP = signal.filtfilt(d, c, aceleracion_x_filtrada_HP)
                    aceleracion_y_filtrada_LP = signal.filtfilt(d, c, aceleracion_y_filtrada_HP)
                    aceleracion_z_filtrada_LP = signal.filtfilt(d, c, aceleracion_z_filtrada_HP)

                    fx, Pxxx_filtrado_LP = signal.periodogram(aceleracion_x_filtrada_LP, fs)
                    fy, Pxxy_filtrado_LP = signal.periodogram(aceleracion_y_filtrada_LP, fs)
                    fz, Pxxz_filtrado_LP = signal.periodogram(aceleracion_z_filtrada_LP, fs)

                    Pxxx_dB = 10 * np.log10(Pxxx_filtrado_LP)
                    Pxxy_dB = 10 * np.log10(Pxxy_filtrado_LP)
                    Pxxz_dB = 10 * np.log10(Pxxz_filtrado_LP)

                    idx_max_x = np.argmax(Pxxx_dB)
                    idx_max_y = np.argmax(Pxxy_dB)
                    idx_max_z = np.argmax(Pxxz_dB)

                    f_max_x = fx[idx_max_x]
                    f_max_y = fy[idx_max_y]
                    f_max_z = fz[idx_max_z]

                    max_power = np.maximum.reduce([Pxxx_dB[idx_max_x], Pxxy_dB[idx_max_y], Pxxz_dB[idx_max_z]])

                    potMax.append(max_power)
                    frecDom.append(f_max_x if max_power == Pxxx_dB[idx_max_x] else
                                            (f_max_y if max_power == Pxxy_dB[idx_max_y] else f_max_z))

        # Calcular medias
        media_potMax = statistics.mean(potMax) if potMax else np.nan
        media_frecDom = statistics.mean(frecDom) if frecDom else np.nan

        # Definición de la función de probabilidad de bradicinesia
        def probabilidad_bradicinesia(f):
            if f <= lim_inf_brad:
                return 1.0
            elif f <= lim_sup_brad:
                P_start = 1.0
                P_end = 0.05
                f_start = lim_inf_brad
                f_end = lim_sup_brad
                return P_start + (P_end - P_start) / (f_end - f_start) * (f - f_start)
            else:
                P_start = 0.05
                P_end = 0.0
                f_start = lim_sup_brad
                f_end = 1.5 * lim_sup_brad
                return max(P_start + (P_end - P_start) / (f_end - f_start) * (f - f_start), 0.0)

        # Calcular la probabilidad de bradicinesia
        probabilidad = probabilidad_bradicinesia(media_frecDom) * 100
        
        Bradykinesia(subject_id=id_participant, probability = probabilidad).save()