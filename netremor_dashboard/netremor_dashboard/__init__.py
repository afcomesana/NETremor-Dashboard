import os
from django.conf import settings
os.environ['DJANGO_SETTINGS_MODULE'] = 'netremor_dashboard.settings'

# Check if the directory where the data files will be stored exists
# If the directory doesn't exists, create it:
if not os.path.isdir(settings.DATAFILES_DIR):
    os.mkdir(settings.DATAFILES_DIR, 0o755)
    
if not os.path.isdir(settings.IMUFILES_DIR):
    os.mkdir(settings.IMUFILES_DIR, 0o755)
    
if not os.path.isdir(settings.TREMOR_FILES_DIR):
    os.mkdir(settings.TREMOR_FILES_DIR, 0o755)