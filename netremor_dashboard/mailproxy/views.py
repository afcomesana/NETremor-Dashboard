import os
from dotenv import load_dotenv

import utils

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest, HttpResponseForbidden, HttpResponse, HttpResponseServerError

load_dotenv()
API_KEY = os.getenv("MAILPROXY_API_KEY")

@csrf_exempt
def index(request):
    
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid method.")

    try:
        if request.META["HTTP_MAILPROXY_API_KEY"] != API_KEY:
            return HttpResponseForbidden("API key is not valid.")
    
    except KeyError:
        return HttpResponseForbidden("Missing API key.")
    
    try:
        email_from    = request.POST["email_from"]
        email_to      = request.POST["email_to"]
        email_subject = request.POST["email_subject"]
        email_body    = request.POST["email_body"]
        
        try:    
            utils.send_mail(email_from, email_to, email_subject, email_body)
            return HttpResponse("OK")
        
        except Exception as e:
            utils.write_log(f"Could not send email from proxy: {e}", "mailproxy", utils.LOG_ERROR)
            return HttpResponseServerError("Could not send email.")
    
    except KeyError as key:
        return HttpResponseBadRequest(f"Missing required field {key}")
    