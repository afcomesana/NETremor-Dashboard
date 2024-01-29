from pymongo.mongo_client import MongoClient
import pprint

uri      = "mongodb://138.4.22.25:27017"
# uri      = "mongodb://172.16.0.6:27017"
client   = MongoClient(uri)
database = client["sth_netremor"]

# databases = client.list_database_names()

# for collection in database.list_collection_names():
#     print(collection)    


ambulatory_collection = database["sth_ambulatory_data"]

ambulatory_collection_acc  = database["sth_ambulatory_data_accelerometer"]
ambulatory_collection_gyro = database["sth_ambulatory_data_gyroscope"]

# for record in collection.find():
#     pprint.pprint(record)