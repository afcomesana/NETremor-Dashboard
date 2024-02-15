from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.conf import settings
from dashboard.models import Verification
from django.urls import reverse

from utils import get_random_string

import re
import requests

def user_exists(username):
    if re.search("@", username):
        return User.objects.filter(email = username).exists()
        
    return User.objects.filter(username = username).exists()

def is_email_domain_valid(email):
    allowed_domains_matchted = list(
        filter(
            lambda email_domain: re.search(rf"\@{email_domain}$", email),
            settings.ALLOWED_EMAIL_DOMAINS
        )
    )

    return len(allowed_domains_matchted) > 0

def is_password_valid(password):
    
    # Minimum length:
    if len(password) < 8: return False
    
    # At least 1 uppercase letter:
    if not re.search(r"[A-Z]", password): return False
    
    # At least 1 lowercase letter:
    if not re.search(r"[a-z]", password): return False
    
    # At least 1 number:
    if not re.search(r"[0-9]", password): return False
    
    # At least 1 strange character:
    if not re.search(r"[!@#$%&/()_-]", password): return False
    
    return True
    

def login_user(request, template, context, form_fields):
    
    # Get username and password from form
    username, password = form_fields.values()
    
    # Check that is reigstered
    if not user_exists(username):
        context["login_error_message"] = "No existe un usuario con ese nombre de usuario o correo electrónico. Por favor, crea una cuenta."
        return render(request, template, context)

    # Check the login method: email or username
    if re.search("@", username):
        username = User.objects.get(email = username)
        
    user = authenticate(request, username = username, password = password)
    
    # If authentication process fails:
    if user is None:
        context["login_error_message"] = "La contraseña es incorrecta. Por favor, inténtalo de nuevo."
        return render(request, template, context)
    
    # Check if the user has verified its account:
    try:
        if not user.verification.is_verified:
            context["login_error_message"] = "La cuenta no está verificada. <a style='text-decoration: underline;' href='%s'>Haz click aquí para reenviar el correo de verificación.</a>" % reverse("dashboard:verification_form")
            
        
    except Verification.DoesNotExist:
        if user.is_superuser:
            pass
        
        else:
            context["login_error_message"] = "La cuenta no está verificada. <a style='text-decoration: underline;' href='%s'>Haz click aquí para reenviar el correo de verificación.</a>" % reverse("dashboard:verification_form")
            return render(request, template, context)
    
    login(request, user)
    
    return redirect("dashboard:index")
    
def register_user(request, template, context, form_fields):
    username, email, password, password_repeat = form_fields.values()
    
    # Validate username
    suggested_username = re.sub(r'[^a-zA-Z0-9\_\.]', "_", username)
    if suggested_username != username:
        suggested_username = re.sub(r'[_]+', "_", suggested_username)
        
        context["register_error_message"] = "El nombre de usuario contiene caracteres no admitidos. Nombre de usuario sugerido: %s" % suggested_username
        return render(request, template, context)
    
    if user_exists(username):
        context["register_error_message"] = "El nombre de usuario ya existe. Por favor, elige otro nombre de usuario."
        return render(request, template, context)
    
    # Validate email:
    if not is_email_domain_valid(email):
        register_error_message = "El dominio del correo electrónico no es válido. Los correos permitidos son "
        register_error_message += ", ".join(settings.ALLOWED_EMAIL_DOMAINS[:-1])
        register_error_message += " y %s." % settings.ALLOWED_EMAIL_DOMAINS[-1]
        context["register_error_message"] = register_error_message
        
        return render(request, template, context)
    
    if user_exists(email):
        context["register_error_message"] = "Este correo electrónico ya está en uso."
        return render(request, template, context)
    
    # Validate password:
    if not is_password_valid(password):
        context["register_error_message"] = "La contraseña no cumple los requerimientos. Por favor, elige una contraseña adecuada."
        return render(request, template, context)
    
    if password != password_repeat:
        context["register_error_message"] = "Las contraseñas no coinciden."
        return render(request, template, context)
    
    user = User.objects.create_user(username, email, password)
    user.save()
    
    user_verification = Verification(user=user, code=get_random_string(settings.VERIFICATION_CODE_LENGTH))
    user_verification.save()
    send_verification_email(user)
    
    
    # request.session["registered_user_email"] = user.email
    
    response = redirect("dashboard:verification_form")
    response.set_cookie("registered_user_email", user.email, max_age=10)
    return response


def send_verification_email(user):
    data = {
        "email_to": user.email,
        "email_from": "NETremor <netremor@oriontech.es>",
        "email_subject": "Verificación de cuenta",
    }
    
    email_message  = "Hola %s,\n\n" % user.username
    email_message += "Te has registrado correctamente en la plataforma de NETremor.\nPara verificar tu cuenta y poder utilizar la plataforma debes acceder a la siguiente dirección:\n\n"
    email_message +=  "https://netremor.oriontech.es/verification/%s/%s/\n\n" % (user.id, user.verification.code)
    email_message += "Con cualquier duda, puedes enviar un correo a la siguiente dirección:\n"
    email_message += "alberto.comesana@csic.es\n\n"
    email_message += "Un saludo."
    
    data["email_message"] = email_message
    
    req = requests.post("https://mailproxy.oriontech.es", json = data)
    
    print(req.text)
    
