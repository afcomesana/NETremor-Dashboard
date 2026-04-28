from pymongo.mongo_client import MongoClient

uri      = "mongodb://138.4.22.25:27017"
client   = MongoClient(uri)

database = client["sth_netremor"]

ambulatory_collection      = database["sth_ambulatory_data"]
ambulatory_collection_acc  = database["sth_ambulatory_data_accelerometer"]
ambulatory_collection_gyro = database["sth_ambulatory_data_giroscope"]
