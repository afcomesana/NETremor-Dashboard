import db_mongo

record = db_mongo.ambulatory_collection_gyro.find_one({})
print(record)