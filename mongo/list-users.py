import db_mongo
import json

# start_time = time.time()
# subjects = db_mongo.ambulatory_collection.find_one({})
subjects = db_mongo.ambulatory_collection.find({"name": {"$ne": "null"}}, {"_id": 0, "name": 1, "subject_id": 1, "diagnosis": 1, "tasks": 1})
subjects = {subject["subject_id"]: subject for subject in subjects if subject}.values()

# Dictionary with all the data that is going to be exported as a JSON
data = {}

for subject in subjects:
    
    data[subject["subject_id"]] = {
        "name": subject["name"],
        "diagnosis": subject["diagnosis"],
        "tasks": {},
    }
    
    for task in subject["tasks"]:
        
        current_task_data = [{
            "accelerometer": db_mongo.ambulatory_collection_acc.find_one({"data_name": task["accelerometerFilename"]})["data"],
            "gyroscope": db_mongo.ambulatory_collection_gyro.find_one({"data_name": task["gyroscopeFilename"]})["data"],
        }]
        
        if task["taskName"] not in data[subject["subject_id"]]["tasks"]:
            data[subject["subject_id"]]["tasks"][task["taskName"]] = current_task_data
        else:
            data[subject["subject_id"]]["tasks"][task["taskName"]] += current_task_data


with open("data.json", "w") as output_file:
    output_file.write(json.dumps(data))
