from db_mongo import database

subject_view = database["sujeto"]
continuous = database["sth_continuous_data_gyroscope"]

print(continuous.find_one({}))