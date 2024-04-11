# DJANGO
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404, HttpResponseBadRequest, HttpResponseServerError, HttpResponseForbidden
from django.template import loader
from endpoint.models import Subject, Record, Datafile, Task, Datafile_task_rel
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.exceptions import ObjectDoesNotExist

from .utils import save_subject, process_record_data

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
from scipy import signal
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
    body_temp_filepath = os.path.join(settings.DATAFILES_DIR, "%s.json" % uuid.uuid1().hex)
    default_storage.save(body_temp_filepath, request.FILES["body.json"])
    
    with open(body_temp_filepath, "r") as file:
        body_data = json.load(file)
    
    os.remove(body_temp_filepath)
    
    # Get tasks from the all the data:
    try:
        recorded_tasks = body_data.pop("recorded_tasks")
        if len(recorded_tasks) == 0:
            return HttpResponseBadRequest("No hay tareas asociadas.")

    except KeyError:
        return HttpResponseBadRequest("Falta el campo 'recordedTasks' en la solicitud.")


    # Get the defined added_on timestamp of this ambulatory record:    
    try:
        record_added_on = body_data.pop("record_added_on")
        
        # Parse the received timestamp in milliseconds to an object that django can understand:
        record_added_on = datetime.fromtimestamp(record_added_on/1000).astimezone(timezone(settings.TIME_ZONE))
        
    except KeyError:
        return HttpResponseBadRequest("Falta el campo 'record_added_on' en la solicitud.")
    
    # Record ID in this database model is generated automatically
    del body_data["record_id"]
    
    # Standarize tasks IDs and names to avoid repetitions and inconsistencies when talking about the same task
    # among different sources and records:
    save_tasks(recorded_tasks)
    
    # Save/update subject in database:
    try:
        subject = save_subject(body_data)
        
    # Some of the mandatory fields is not present in the request:
    except KeyError as error_message:
        print("Key error:", error_message)
        return HttpResponseBadRequest(error_message)
    
    
    # Create and attach record to the subject:
    try:
        record = Record(subject = subject, type="ambulatory", added_on=record_added_on)
        record.save()
    except Exception as e:
        print("Unknown error: ", e)
        return HttpResponseServerError
    

    # Save raw data files and corresponding tasks:
    for task in recorded_tasks:
        
        # task will be a dictionary with information about the task
        # description, task_id, task_name, files corresponding to
        # each sensor, and so on
        
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
                
                # TODO: do this sorting in a parallel process to lighten waiting time
                # Sort the data based on timestamp (4th column, columns 0 indexed)
                csvsort(filepath, [3])
                
                # Store data file instance in database:
                datafile = Datafile(record=record, name=filename, sensor=sensor)
                datafile.save()
                
                # Store the relation between the task, the record and the datafile:
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
    
    
    # Execute parallelized processes to avoid high response time
    # (number of processes defaults to os.cpu_count())
    threading.Thread(target=process_record_data, args=[record]).start()    
    
    
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