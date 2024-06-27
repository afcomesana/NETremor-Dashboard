from db_mongo import database
import bson
import math

# subject_view = database["sujeto"]
# continuous = database["sth_continuous_data_gyroscope"]
# print(continuous.find_one({}))

# for name in database.list_collection_names():
#     print(name)

# bson_data = bson.BSON.encode(bucket)
# print("Amount of samples:", len(bucket["data"]), "Size in bytes:", len(bson_data))

coll = database["sth_continuous_data_gyroscope"]

initial_timestamp = "1712330789524"
final_timestamp   = "1712334377724"

nsamples = 1000

for bucket in coll.find({}):
    print(bucket["first_timestamp"])

buckets = coll.find({"first_timestamp": {"$gt": initial_timestamp, "$lt": final_timestamp}})

for bucket in buckets:
    print(bucket["first_timestamp"])
    # last_timestamp = None
    
    # print(bucket["bucket_id"])
    
    # for item in bucket["data"]:
    #     timestamp = item["timestamp"]
        
    #     if last_timestamp is None:
    #         last_timestamp = timestamp
    #         continue
        
    #     gap = timestamp - last_timestamp
        
    #     if gap > 28:
    #         print("Gap", gap)
            
    #     last_timestamp = timestamp

# buckets = [[item for item in bucket if item["timestamp"] >= initial_timestamp or item["timestamp"] <= final_timestamp] for bucket in buckets]

# initial_timestamp = int(initial_timestamp)
# final_timestamp   = int(final_timestamp)
# time_span         = final_timestamp - initial_timestamp
# time_step         = time_span / nsamples

# for bucket in buckets:
#     bucket_initial_timestamp = max(initial_timestamp, int(bucket["first_timestamp"]))
#     bucket_final_timestamp   = max(final_timestamp, bucket["data"][-1]["timestamp"])
#     bucket_time_range        = bucket_final_timestamp - bucket_initial_timestamp
#     bucket_nsamples          = math.ceil(nsamples*(bucket_time_range/time_span))
    
