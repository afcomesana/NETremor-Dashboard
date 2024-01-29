# DJANGO
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404, HttpResponseBadRequest, HttpResponseServerError, HttpResponseForbidden
from django.template import loader
from endpoint.models import Subject, Record, DataFile
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.exceptions import ObjectDoesNotExist

from .utils import save_subject

# OTHER PYTHON LIBRARIES
import os
import re
import json
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
    
    # Validate API_KEY
    try:
        if request.META["HTTP_NETREMOR_API_KEY"] != API_KEY:
            return HttpResponseForbidden("Clave de API incorrecta.")
    except KeyError:
        return HttpResponseForbidden("No se ha enviado clave de API.")
    
    if len(request.FILES) == 0:
        return HttpResponseBadRequest("No hay archivos de datos.")
    
    # Split tasks and subject data:
    try:
        post_fields = request.POST.copy()
        
        tasks = post_fields.pop("tasks")[0]
        tasks = json.loads(tasks)
        
        if len(tasks) == 0: return HttpResponseBadRequest("No hay tareas asociadas.")
        
    except KeyError:
        return HttpResponseBadRequest("Falta el campo 'tasks' en la solicitud.")
    
    record_added_on = post_fields.pop("recordAddedOn")[0]
    
    # Save/update subject in database:
    try:
        subject = save_subject(post_fields)
    except KeyError as error_message:
        return HttpResponseBadRequest(error_message)
    
    # Create record:
    try:
        record = Record(subject = subject, type="ambulatory")
        record.save()
    except Exception as e:
        print("Unknown error: ", e)
        return HttpResponseServerError

    # Save data files and corresponding tasks:
    for index, task in enumerate(tasks):
        for sensor in SENSOR_NAMES:
            try:
                # Store the file in the data files directory:
                file     = request.FILES[task["%sFilename" % sensor]]
                
                filename  = [utils.str2filename(subject.id), record_added_on, sensor, str(index)]
                
                if "taskName" in task.keys():
                    filename += [utils.str2filename(task["taskName"])]
                    
                filename  = "-".join(filename)
                filename += ".csv"
                filepath  = os.path.join(settings.DATA_FILES_DIR, filename)
                
                if os.path.exists(filepath):
                    print("File", filename, "already exists. Data not saved.")
                    continue
                
                default_storage.save(filepath, file)
                
                # Store data file instance in database:
                data_file_args = {
                    "record": record,
                    "name": filename,
                    "sensor": sensor,
                }
                
                if "trial" in task.keys():
                    data_file_args["trial"] = task["trial"]
                
                if "taskId" in task.keys():
                    data_file_args["task_id"] = task["taskId"]
                    
                    if "taskName" in task.keys():
                        data_file_args["task_name"] = task["taskName"]
                        
                    if "taskDescription" in task.keys():
                        data_file_args["task_description"] = task["taskDescription"]

                data_file = DataFile(**data_file_args)
                data_file.save()
                
            except KeyError:
                print("Current task doesn't have %s file" % sensor)
                continue

    if record.datafile_set.count() == 0:
        record.delete()
        
        
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
    
    
    post_fields = request.POST.copy()
    
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
                continue
            
            stored_filename = record.datafile_set.filter(sensor = sensor)

            # No files yet:
            if stored_filename.count() == 0:
                filename = "%s-%s" % (subject.id, file)
                filename = re.sub(r'\.dat$', ".csv", filename)
                
                # Store data file instance in database:
                data_file_args = {
                    "record": record,
                    "name": filename,
                    "sensor": sensor
                }
                
                data_file = DataFile(**data_file_args)
                data_file.save()
                
            # DataFile already exists:
            else:
                filename = stored_filename.get(sensor=sensor).name

            filepath = os.path.join(settings.DATA_FILES_DIR, filename)
            
            # First creating this file
            if not os.path.exists(filepath):
                default_storage.save(filepath, request.FILES[file])
                
            # File exists, append incoming content to the existing one
            else:
                temporary_filepath = os.path.join(settings.DATA_FILES_DIR, "temporary-%s" % filename)
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
                    
    except Exception as e:
        return HttpResponseServerError("Unexpected error in server.")
        

    return HttpResponse(200)



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