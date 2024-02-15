from pymongo.mongo_client import MongoClient
import pprint

uri      = "mongodb://138.4.22.25:27017"
# uri_for_sending_data      = "mongodb://138.4.22.25:8000"
client   = MongoClient(uri)

database = client["sth_netremor_prueba"]
ambulatory_collection      = database["sth_ambulatory_data"]
ambulatory_collection_acc  = database["sth_ambulatory_data_accelerometer"]
ambulatory_collection_gyro = database["sth_ambulatory_data_gyroscope"]

# databases = client.list_database_names()

# for collection_name in database.list_collection_names():
#     print(collection_name)
#     collection_instance = database[collection_name]
    
#     for item in collection_instance.find():
#         print(item)
        

# for record in collection.find():
#     pprint.pprint(record)