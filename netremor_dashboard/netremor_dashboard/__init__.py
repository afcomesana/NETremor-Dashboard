import os
from django.conf import settings
os.environ['DJANGO_SETTINGS_MODULE'] = 'netremor_dashboard.settings'

# Check if the directory where the data files will be stored exists
# If the directory doesn't exists, create it:
if not os.path.isdir(settings.DATA_FILES_DIR):
    os.mkdir(settings.DATA_FILES_DIR, 755)