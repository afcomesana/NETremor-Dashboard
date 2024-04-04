# DJANGO
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404, HttpResponseBadRequest, HttpResponseServerError, HttpResponseForbidden
from django.template import loader
from endpoint.models import Subject, Record, Datafile, Task, Datafile_task_rel
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.exceptions import ObjectDoesNotExist

from .utils import save_subject

# OTHER PYTHON LIBRARIES
import os
import re
import json
import time
import uuid
from csvsort import csvsort
from datetime import datetime
from pytz import timezone
from dotenv import load_dotenv
import threading


load_dotenv()
API_KEY      = os.getenv("API_KEY")
SENSOR_NAMES = list(map(lambda sensor: sensor[0], settings.SENSOR_CHOICES))

@csrf_exempt # disable default csrf security checks from django
def ambulatory(request):
    
    # Only allow request with POST method:
    if request.method != "POST":
        return HttpResponseBadRequest("Método no válido.")
    
    # Validate API_KEY
    try:
        if request.META["HTTP_NETREMOR_API_KEY"] != API_KEY:
            return HttpResponseForbidden("Clave de API incorrecta.")
        
    # No API KEY header
    except KeyError:
        return HttpResponseForbidden("No se ha enviado clave de API.")
    
    # No files sent with the request
    if len(request.FILES) == 0:
        return HttpResponseBadRequest("No se han enviado archivos.")
    
    # Get subject and record data:
    body_filepath = os.path.join(settings.DATAFILES_DIR, "%s.json" % uuid.uuid1().hex)
    default_storage.save(body_filepath, request.FILES["body.json"])
    
    with open(body_filepath, "r") as file:
        body_data = json.load(file)
    
    os.remove(body_filepath)
    
    # Split tasks and subject data:
    try:
        recorded_tasks = body_data.pop("recorded_tasks")
        if len(recorded_tasks) == 0:
            return HttpResponseBadRequest("No hay tareas asociadas.")
        
    except KeyError:
        return HttpResponseBadRequest("Falta el campo 'recordedTasks' en la solicitud.")

    
    try:
        record_added_on = body_data.pop("record_added_on")
        record_added_on = datetime.fromtimestamp(record_added_on/1000).astimezone(timezone(settings.TIME_ZONE))
    except KeyError:
        return HttpResponseBadRequest("Falta el campo 'record_added_on' en la solicitud.")
    
    # Record ID in this database model is generated automatically
    del body_data["record_id"]
    
    # Standarize tasks IDs and names to avoid repetitions and inconsistencies when talking about the same task:
    save_tasks(recorded_tasks)
    
    # Save/update subject in database:
    try:
        subject = save_subject(body_data)
        
    # Some of the mandatory fields is not present in the request:
    except KeyError as error_message:
        print("Key error:", error_message)
        return HttpResponseBadRequest(error_message)
    
    
    # Create record:
    try:
        record = Record(subject = subject, type="ambulatory", added_on=record_added_on)
        record.save()
    except Exception as e:
        print("Unknown error: ", e)
        return HttpResponseServerError
    

    # Save data files and corresponding tasks:
    for task in recorded_tasks:
        for sensor in SENSOR_NAMES:
            try:
                # Store the file in the data files directory:
                file      = request.FILES[task["%s_filename" % sensor]]
                filename  = file.name
                filepath  = os.path.join(settings.DATAFILES_DIR, filename)
                
                if os.path.exists(filepath):
                    print("File", filename, "already exists. Data not saved.")
                    continue
                
                default_storage.save(filepath, file)
                
                # Sort the data based on timestamp (4th column, columns 0 indexed)
                csvsort(filepath, [3])
                
                # Store data file instance in database:
                datafile = Datafile(record=record, name=filename, sensor=sensor)
                datafile.save()
                
                if "task_id" in task.keys():
                    Datafile_task_rel(
                        record=record,
                        datafile=datafile,
                        task=Task.objects.get(id=task["task_id"]),
                        trial=task["trial"]
                    ).save()
                    
                
            except KeyError:
                print("Current task doesn't have %s file" % sensor)
                continue
        
    if record.datafile_set.count() == 0:
        record.delete()
        return HttpResponseBadRequest("This record is already saved.")
    
    # Trigger computation of spectrograms upon received data without
    # blocking the response sending
    threading.Thread(target = compute_spectrogram, args = [record]).start()

    return HttpResponse("OK")

@csrf_exempt
def continuous(request):
    
    # Only allow request with POST method:
    if request.method != "POST":
        return HttpResponseBadRequest("Incorrect method")
    
    if not request.FILES:
        return HttpResponseBadRequest("No file was sent.")
    
    # Validate API_KEY
    try:
        if request.META["HTTP_NETREMOR_API_KEY"] != API_KEY:
            return HttpResponseForbidden("Incorrect API KEY.")
    except KeyError:
        return HttpResponseForbidden("Missing api key.")
    
    
    
    # Get subject and record data:
    body_filepath = os.path.join(settings.DATAFILES_DIR, "%s.json" % uuid.uuid1().hex)
    default_storage.save(body_filepath, request.FILES["body.json"])
    
    with open(body_filepath, "r") as file:
        body_data = json.load(file)
    
    
    os.remove(body_filepath)
    
    try:
        # Save recorded tasks during continuous record:
        recorded_tasks = body_data.pop("recorded_tasks")
        save_tasks(recorded_tasks)
    except KeyError:
        recorded_tasks = []
        
            
    try:
        record_added_on = body_data.pop("record_added_on")
        record_added_on = datetime.fromtimestamp(record_added_on/1000).astimezone(timezone(settings.TIME_ZONE))
    except KeyError:
        return HttpResponseBadRequest("Falta el campo 'record_added_on' en la solicitud.")
    
    
    # Save/update subject in database:
    try:
        subject = save_subject(body_data)
    except KeyError as error_message:
        return HttpResponseBadRequest("Key error in request: %s" % error_message)
    
    # Create or retrieves record:
    record, _ = subject.record_set.get_or_create(type="continuous", defaults={"added_on": record_added_on})
    
    try:
            
        for file in request.FILES:

            # Do not save files whose sensor could not be identified:
            sensor = next(filter(lambda sensor_name: sensor_name in file, SENSOR_NAMES), None)
            if sensor is None:
                print("Skipping not recognized sensor file: %s." % file)
                continue
            
            # Get or create database instance:
            try:
                datafile = record.datafile_set.get(sensor = sensor)
            except Datafile.DoesNotExist:
                filename = re.sub(r'\.dat$', ".csv", file)
                
                # Store data file instance in database:
                datafile_args = {
                    "record": record,
                    "name": filename,
                    "sensor": sensor
                }
                
                datafile = Datafile(**datafile_args)
                datafile.save()
                
            # Save tasks recorded in continuous record:
            if len(recorded_tasks) > 0:
                for task in recorded_tasks:
                    Datafile_task_rel(
                        record=record,
                        datafile=datafile,
                        task=Task.objects.get(id=task["task_id"]),
                        starts_at=datetime.fromtimestamp(task["starts_at"]/1000).astimezone(timezone(settings.TIME_ZONE)).isoformat(sep=" ", timespec="milliseconds"),
                        ends_at=datetime.fromtimestamp(task["ends_at"]/1000).astimezone(timezone(settings.TIME_ZONE)).isoformat(sep=" ", timespec="milliseconds"),
                    ).save()

            filepath = os.path.join(settings.DATAFILES_DIR, datafile.name)
            
            # First creating this file
            if not os.path.exists(filepath):
                default_storage.save(filepath, request.FILES[file])
                
            # File exists, append incoming content to the existing one
            else:
                temporary_filepath = os.path.join(settings.DATAFILES_DIR, "temporary-%s" % datafile.name)
                default_storage.save(temporary_filepath, request.FILES[file])
                
                incoming_file = open(temporary_filepath, "r")
                
                # Remove first row with column names:
                incoming_file_content = incoming_file.read()
                column_names = re.search(r'[a-z]\n', incoming_file_content)
                
                if not column_names is None:
                    _, end_row_index = column_names.span()
                    incoming_file_content = incoming_file_content[end_row_index:]
                    
                incoming_file.close()
                
                os.remove(temporary_filepath)
                        
                # Append context to continuous record
                with open(filepath, "a") as stored_file:
                    stored_file.write(incoming_file_content)
                    
            # Sort the data based on timestamp (4th column, columns 0 indexed)
            csvsort(filepath, [3])
            
    except Exception as e:
        print("Error during continuous record saving process:", e)
        return HttpResponseServerError("Unexpected error in server.")
        

    return HttpResponse(200)


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
    for task in tasks_to_store:
        Task(**task).save()

def get_ambulatory_record_filename(basename, extension = "csv", index = 0):
    
    filepath = RECEIVED_FILES_DIRECTORY + "%s-%s.%s" % (basename, index, extension)
    
    # Check that the current filepath does not exists:
    if os.path.exists(filepath):
        return get_ambulatory_record_filename(basename,  extension, index + 1)
    
    return filepath


def index(request):
    subjects_list = Subject.objects.all()
    # template = loader.get_template("dashboard/index.html")
    context = {
        "subjects_list": subjects_list
    }
    
    # return HttpResponse(template.render(context, request))
    return render(request, "dashboard/index.html", context)

def records(request, subject_id):
    subject = get_object_or_404(Subject, pk=subject_id)
    return render(request, "dashboard/records.html", {"subject": subject})

def compute_spectrogram(entity):
    """
    Given an entity (record|datafile), compute the spectrograms of the raw sensor data.
    
    If the entity is a Record:
        1. Fetch all the datafiles associated with the record.
        2. Compute spectrogram for each file in the record.
        
    If the entity is a Datafile:
        Store the results in a CSV file with the corresponding timestamp and axis for each spectrogram time slice.

    Args:
        entity (Record|Datafile): The record or datafile whose raw data is going to be used to compute the spectrogram(s).
    """
    
        
    if isinstance(entity, Record):
        for datafile in entity.datafile_set.all():
            threading.Thread(target=compute_spectrogram, args=[datafile]).start()
        
    if isinstance(entity, Datafile):
        datafile_path = os.path.join(settings.DATAFILES_DIR, datafile.name)
        
        with open(datafile_path) as file:
            
            ######################################################################
            # SPECTROGRAM COMPUTATION
            ######################################################################
            
            # def band_pass_filter(data, low_pass_frequency, high_pass_frequency, sampling_frequency):
            # # N: order of the filter
            # # Wn: critical frequency
            # b, a = signal.butter(N=4, Wn=[low_pass_frequency, high_pass_frequency], btype="bandpass", fs=sampling_frequency)
            # # returns numerator and denominator of the polynomials of the IIR filter

            # # filtfilt the input acceleracion_(x|y|z) filtered
            # return signal.filtfilt(b, a, signal.filtfilt(b, a, data))
            
            # DATA_DIR = "ambulatory-data/b261383e019eba47c32416a232c3181c94da4dab457878b20cd0f10797203c10-ambulatory-38"

            # # Select a file corresponding to the task of brushing teeth;
            # TEST_FILE = next(filter(lambda filename: re.search(r"[0-9]+\.csv$", filename) is not None, os.listdir(DATA_DIR)))

            # with open(os.path.join(DATA_DIR, TEST_FILE)) as file:
            #     next(file)
            #     data = list(map(lambda line: float(line.split(",")[0]), file))
                        
            # # Bandpass filter to remove voluntary motion and noise:

            # from utils import bandpass_filter

            # filtered_data = bandpass_filter(data, 2, 8, 30)

            # t = np.arange(len(data))

            # plt.plot(t, data)
            # plt.plot(t, filtered_data)
            
            
            # # Compute spectrogram:
            # SAMPLE_FREQ    = 30 # Herz
            # SAMPLE_PERIOD  = 1 / SAMPLE_FREQ # seconds
            # HOP_SECONDS    = 1 # seconds
            # HOP_SAMPLES    = HOP_SECONDS*SAMPLE_FREQ
            # WINDOW_SECONDS = 2
            # WINDOW_SIZE    = WINDOW_SECONDS*SAMPLE_FREQ
            # OVERSAMPLING_FACTOR = 16

            # fig, ax1 = plt.subplots()

            # gaussian_window = signal.windows.gaussian(WINDOW_SIZE, std=12, sym=True)

            # SFT = signal.ShortTimeFFT(gaussian_window, hop=HOP_SAMPLES, fs=SAMPLE_FREQ, mfft=OVERSAMPLING_FACTOR*SAMPLE_FREQ, scale_to="psd")
            # psd = SFT.spectrogram(filtered_data)

            # t_lo, t_hi = SFT.extent(len(data))[:2] # time range of the spectrogram
            # print(SFT.p_num(len(data))) # number of time slices
            # print(SFT.delta_t) # in seconds
            # print(SFT.delta_f) # in Hz

            # ax1.set(xlim=(t_lo, t_hi))


            # psd_db = 10 * np.log10(np.fmax(psd, 1e-4))
            # im1 = ax1.imshow(psd_db, origin="lower", aspect="auto", extent=SFT.extent(len(data)), cmap="magma")
