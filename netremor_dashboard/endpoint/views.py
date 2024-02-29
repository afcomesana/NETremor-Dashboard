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
from csvsort import csvsort
from datetime import datetime
from pytz import timezone
from dotenv import load_dotenv
import utils

load_dotenv()
API_KEY      = os.getenv("API_KEY")
SENSOR_NAMES = list(map(lambda sensor: sensor[0], settings.SENSOR_CHOICES))

@csrf_exempt # disable default csrf security checks from django
def ambulatory(request):
    
    # Only allow request with POST method:
    if request.method != "POST":
        return HttpResponseBadRequest("Método no válido.")
    
    print("Check 1")
    # Validate API_KEY
    try:
        if request.META["HTTP_NETREMOR_API_KEY"] != API_KEY:
            return HttpResponseForbidden("Clave de API incorrecta.")
    except KeyError:
        return HttpResponseForbidden("No se ha enviado clave de API.")
    
    if len(request.FILES) == 0:
        return HttpResponseBadRequest("No hay archivos de datos.")
    print("Check 2")
    
    # Split tasks and subject data:
    try:
        post_fields = request.POST.copy()
        
        recorded_tasks = post_fields.pop("recordedTasks")[0]
        recorded_tasks = json.loads(recorded_tasks)
        
        if len(recorded_tasks) == 0:
            return HttpResponseBadRequest("No hay tareas asociadas.")
        
    except KeyError:
        return HttpResponseBadRequest("Falta el campo 'recordedTasks' en la solicitud.")
    
    print("Check 3")
    
    try:
        record_added_on = post_fields.pop("recordAddedOn")[0]
        
    except KeyError:
        return HttpResponseBadRequest("Falta el campo 'recordAddedOn' en la solicitud.")
    
    print("Check 4")
    save_tasks(recorded_tasks)
    print("Check 5")
    
    # Save/update subject in database:
    try:
        subject = save_subject(post_fields)
    except KeyError as error_message:
        print("Key error:", error_message)
        return HttpResponseBadRequest(error_message)
    print("Check 6")
    
    # Create record:
    try:
        record = Record(subject = subject, type="ambulatory")
        record.save()
    except Exception as e:
        print("Unknown error: ", e)
        return HttpResponseServerError
    print("Check 7")

    # Save data files and corresponding tasks:
    for index, task in enumerate(recorded_tasks):
        for sensor in SENSOR_NAMES:
            try:
                # Store the file in the data files directory:
                file      = request.FILES[task["%sFilename" % sensor]]
                filename  = [utils.str2filename(subject.id), record_added_on, sensor, str(index)]
                
                if "taskId" in task.keys():
                    filename += [utils.str2filename(task["taskId"])]
                    
                filename  = "-".join(filename)
                filename += ".csv"
                filepath  = os.path.join(settings.DATAFILES_DIR, filename)
                
                if os.path.exists(filepath):
                    print("File", filename, "already exists. Data not saved.")
                    continue
                
                default_storage.save(filepath, file)
                
                # Store data file instance in database:
                datafile = Datafile(record=record, name=filename, sensor=sensor)
                datafile.save()
                
                if "taskId" in task.keys():
                    Datafile_task_rel(
                        record=record,
                        datafile=datafile,
                        task=Task.objects.get(id=task["taskId"]),
                        trial=task["trial"]
                    ).save()
                    
                
            except KeyError:
                print("Current task doesn't have %s file" % sensor)
                continue
        
    print("check 8")
    if record.datafile_set.count() == 0:
        record.delete()
        return HttpResponseBadRequest("This record is already saved.")
        
        
    return HttpResponse("OK")


@csrf_exempt
def continuous(request):
    print(request.FILES)
    
    return HttpResponse("OK")
    
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
    
    post_fields = request.POST.copy()
    
    try:
        # Save recorded tasks during continuous record:
        recorded_tasks = post_fields.pop("recordedTasks")[0]
        recorded_tasks = json.loads(recorded_tasks)
        save_tasks(recorded_tasks)
    except KeyError:
        recorded_tasks = []
    
    # Save/update subject in database:
    try:
        subject = save_subject(post_fields)
    except KeyError as error_message:
        return HttpResponseBadRequest("Key error in request: %s" % error_message)
    
    # Create or retrieves record:
    record, _ = subject.record_set.get_or_create(type="continuous")
    
    try:
            
        for file in request.FILES:

            # Do not save files whose sensor could not be identified:
            sensor = next(filter(lambda sensor_name: sensor_name in file, SENSOR_NAMES), None)
            if sensor is None:
                print("Skipping not recognized sensor file.")
                continue
            
            # Get or create database instance:
            try:
                datafile = record.datafile_set.get(sensor = sensor)
            except Datafile.DoesNotExist:
                filename = "%s-%s" % (subject.id, file)
                filename = re.sub(r'\.dat$', ".csv", filename)
                
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
                        task=Task.objects.get(id=task["taskId"]),
                        starts_at=datetime.fromtimestamp(task["startsAt"]/1000).astimezone(timezone(settings.TIME_ZONE)).isoformat(sep=" ", timespec="milliseconds"),
                        ends_at=datetime.fromtimestamp(task["endsAt"]/1000).astimezone(timezone(settings.TIME_ZONE)).isoformat(sep=" ", timespec="milliseconds"),
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
        - taskId
        - taskName
        - taskDescription
    """
    for task in incoming_tasks:
        if "taskId" in task.keys():
            task["taskId"] = task["taskId"].upper()
    
    # Create list with each item being the arguments for creating the task that is not yet in the database
    current_stored_tasks = Task.objects.values_list("id", flat=True).distinct()
    tasks_to_store       = list(map(lambda task: {
        "id": task["taskId"],
        "name": task["taskName"] if "taskName" in task.keys() else None,
        "description": task["taskDescription"] if "taskDescription" in task.keys() else None,
    }, filter(lambda incoming_task: "taskId" in incoming_task.keys() and incoming_task["taskId"] not in current_stored_tasks, incoming_tasks)))
    
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