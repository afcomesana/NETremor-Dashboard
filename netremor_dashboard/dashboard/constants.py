from .utils import login_user, register_user
from django.conf import settings

LOGIN_FORM_FIELDS = {
    "login": {
        "fields": [
            {
                "name": "username",
                "label": "User email or email",
                "type": "text",
                "is_required": True,
                "class": "d-block rounded border w-100",
            },
            {
                "name": "password",
                "label": "Password",
                "type": "password",
                "is_required": True,
                "class": "d-block rounded border w-100",
            },
        ],
        "callback": login_user
    },
    "register": {
        "fields": [
            {
                "name": "username",
                "label": "Username",
                "type": "text",
                "is_required": True,
                "class": "d-block rounded border w-100",
            },
            {
                "name": "email",
                "label": "Email",
                "type": "email",
                "is_required": True,
                "info": "Email address must belong to one of the following domanis: %s o %s" % (", ".join(settings.ALLOWED_EMAIL_DOMAINS[:-1]), settings.ALLOWED_EMAIL_DOMAINS[-1]),
                "class": "d-block rounded border w-100",
            },
            {
                "name": "password",
                "label": "Password",
                "type": "password",
                "is_required": True,
                "info": """Password must have at least:<br>
                    <ul style="padding: 0; padding-left: 15px;">
                        <li id="password-min-characters">8 characters</li>
                        <li id="password-uppercase">1 uppercase letter</li>
                        <li id="password-lowercase">1 lowercase letter</li>
                        <li id="password-number">1 number</li>
                        <li id="password-strange-character">1 of the following characters: !, @, #, $, %, &, /, (, ), _ or -.</li>
                    </ul>""",
                "class": "d-block rounded border w-100",
            },
            {
                "name": "password_repeat",
                "label": "Repeat password",
                "type": "password",
                "is_required": True,
                "class": "d-block rounded border w-100",
            },
        ],
        "callback": register_user
    }
}