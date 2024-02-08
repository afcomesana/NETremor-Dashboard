import os
import csv
from datetime import datetime
from pytz import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netremor_dashboard.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

from endpoint.models import Subject

DATA_FILES_DIR = "./data-files"

subject = Subject.objects.get(name="Alberto Comesaña")
record = subject.record_set.get(type="continuous")

datafiles = record.datafile_set.all()

for datafile in datafiles:
    
    datafile_path = os.path.join(DATA_FILES_DIR, datafile.name)
    
    print("\n\nASSESSING NEW FILE:")

    with open(datafile_path, "r") as file:
        
        previous_timestamp = None
        for line, values in enumerate(file):
            if line == 0:
                continue
            
            x, y, z, timestamp = values.split(",")
            
            timestamp = int(timestamp)
            
            if not previous_timestamp is None:
                if timestamp - previous_timestamp > 1000:
                    timestamp_datetime = datetime.fromtimestamp(timestamp / 1000).astimezone(timezone("Europe/Madrid")).isoformat(sep=" ", timespec="milliseconds")
                    previous_timestamp_datetime = datetime.fromtimestamp(previous_timestamp / 1000).astimezone(timezone("Europe/Madrid")).isoformat(sep=" ", timespec="milliseconds")
                    
                    print("LINE",line,"Lack of record data between", previous_timestamp_datetime, "and", timestamp_datetime, "of", (timestamp - previous_timestamp)/1000, "seconds")
                    
                elif previous_timestamp > timestamp:
                    print("unordered timestamp:", timestamp)
            
            if line > 1:
                previous_timestamp = timestamp