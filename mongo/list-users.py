import connector
import time

# start_time = time.time()

subjects = connector.ambulatory_collection.find({}, {"_id": 0, "subject_id": True, "birth_year": True, "name": True})
subjects = {subject["subject_id"]: subject for subject in subjects if subject}.values()

# end_time = time.time()

# print("Ellapsed time:", end_time - start_time)