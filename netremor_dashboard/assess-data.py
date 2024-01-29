import os
import csv
from datetime import datetime
import pytz

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netremor_dashboard.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

from endpoint.models import Subject

DATA_FILES_DIR = "./data-files"

subject = Subject.objects.get(name="Alberto Comesaña")
record = subject.record_set.get(type="continuous")

datafiles = record.datafile_set.all()

for datafile in datafiles:
    
    if datafile.sensor == "heartRate" or datafile.task_name == "no-task":
        continue

    datafile_path = os.path.join(DATA_FILES_DIR, datafile.name)
    
    timestamps = []

    with open(datafile_path, "r") as data:
        for row in csv.DictReader(data):
            timestamps += [row["timestamp"]]
            
    timestamps.sort()
    
    lost_data = []
    
    for index, timestamp in enumerate(timestamps):
        if index == 0:
            continue
        
        break
        datetimes = [datetime.fromtimestamp(int(timestamps[index - 1]) / 1000), datetime.fromtimestamp(int(timestamp) / 1000)]
        lost_milliseconds = int(timestamp) - int(timestamps[index - 1])
        
        if lost_milliseconds > 1000:
            lost_data += [{"loss":lost_milliseconds, "datetimes": datetimes}]
            
    if len(lost_data) == 0:
        continue
    
    for loss in lost_data:
        print(loss["loss"], "milliseconds", "(",loss["datetimes"][0], " - ", loss["datetimes"][1], ")")

# subjects = Subject.objects.all()

# for subject in subjects:

#     ambulatory_records = subject.record_set.filter(type="ambulatory")
    
#     print("\n\nSujeto:", subject)

#     for record in ambulatory_records:
        
#         datafiles = record.datafile_set.all()
        
#         for datafile in datafiles:
            
#             if datafile.sensor == "heartRate" or datafile.task_name == "no-task":
#                 continue

#             datafile_path = os.path.join(DATA_FILES_DIR, datafile.name)
            
#             timestamps = []

#             with open(datafile_path, "r") as data:
#                 for row in csv.DictReader(data):
#                     timestamps += [row["timestamp"]]
                    
#             timestamps.sort()
            
#             lost_data = []
#             timestamp_span  = []
            
#             for index, timestamp in enumerate(timestamps):
#                 if index == 0:
#                     timestamp_span += [-int(timestamp)]
#                     continue
                    
#                 if index == len(timestamps) - 1:
#                     timestamp_span += [int(timestamp)]
                
#                 lost_milliseconds = int(timestamp) - int(timestamps[index - 1])
                
#                 if lost_milliseconds > 50:
#                     lost_data += [lost_milliseconds]
                    
#             if len(lost_data) == 0:
#                 continue
            
#             timestamp_span = sum(timestamp_span)
            
#             print("\n\nLost data for task", datafile.task_name)
            
#             for millis in lost_data:
#                 print(millis, "milliseconds")
                
#             print("total loss:", sum(lost_data), "ms (", round((sum(lost_data)/timestamp_span)*100, 2), "% )")