import db_mongo
import time

# start_time = time.time()
print(db_mongo.ambulatory_collection.count_documents({}))
# subjects = db_mongo.ambulatory_collection.find_one({})
subjects = db_mongo.ambulatory_collection.find({}, {"_id": 0, "subject_id": True, "birth_year": True, "name": True})
subjects = {subject["subject_id"]: subject for subject in subjects if subject}.values()
print(len(subjects))

# [print(subject) for subject in subjects]
# end_time = time.time()

# print("Ellapsed time:", end_time - start_time)