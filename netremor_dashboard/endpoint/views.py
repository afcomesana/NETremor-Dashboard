# PYTHON LIBRARIES
import os
import json
import uuid
from datetime import datetime
from pytz import timezone
from dotenv import load_dotenv

# CUSTOM MODULES
from endpoint import utils

# DJANGO FRAMEWORK
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.files.storage import default_storage

load_dotenv()
API_KEY = os.getenv("API_KEY")

@csrf_exempt # disable default csrf security checks from django
def save_record(request):

    if request.method != "POST":
        return HttpResponseBadRequest("Método no válido.")
    

    try:
        if request.META["HTTP_NETREMOR_API_KEY"] != API_KEY:
            return HttpResponseForbidden("Clave de API incorrecta.")
        
    except KeyError:
        return HttpResponseForbidden("No se ha enviado clave de API.")
    
    if len(request.FILES) == 0:
        return HttpResponseBadRequest("No se han enviado archivos.")
    
    
    if sum(1 for _ in filter(lambda filename: not os.path.exists(os.path.join(settings.DATAFILES_DIR, filename)), request.FILES)) == 0:
        return HttpResponse("Los archivos enviados ya están guardados.")

    # Data about the subject and record is expected to be sent in the "body.json" file.
    body_filepath = os.path.join(settings.DATAFILES_DIR, "%s.json" % uuid.uuid1().hex)
    default_storage.save(body_filepath, request.FILES["body.json"])
    
    with open(body_filepath, "r") as file:
        body_data = json.load(file)
    
    os.remove(body_filepath)
    
    try:
        recorded_tasks = body_data.pop("recorded_tasks")
        
        # Tasks are saved in its own table to prevent different names and descriptions
        # for the same task ID. Then, tasks in records are retrieved using this table.
        utils.save_tasks_or_positions(recorded_tasks, "task")
        
    except KeyError:
        recorded_tasks = []

    try:
        recorded_positions = body_data.pop("recorded_positions")
        utils.save_tasks_or_positions(recorded_positions, "position")
        
    except KeyError:
        recorded_positions = []


    try:
        record_added_on = body_data.pop("record_added_on")
        record_added_on = datetime.fromtimestamp(record_added_on/1000).astimezone(timezone(settings.TIME_ZONE))
        # TODO: Consider changing database type of record_added_on to integer and do not use datetimes.
        
    except KeyError:
        return HttpResponseBadRequest("Falta el campo 'record_added_on' en la solicitud.")
    
    try:
        delta_t = int(body_data.pop("delta_t"))
    
    except KeyError:
        delta_t = settings.DEFAULT_DELTA_T
    
    try:
        # If the subject already exists, it will be updated.
        subject = utils.save_subject(body_data)
        
    except KeyError as error_message:
        return HttpResponseBadRequest("Key error in request: %s" % error_message)
    
    # The request path will follow the form "/endpoint/<record_type>" or "/endpoint/<record_type>/"
    # Get the record type from the request path to properly call the function that will process the
    # record data.
    record_type          = list(filter(lambda item: bool(item.strip()), request.path.split("/")))[-1]
    save_record_callback = getattr(utils, "save_%s_record" % record_type)

    return save_record_callback(request, subject, recorded_tasks, recorded_positions, record_added_on, delta_t)