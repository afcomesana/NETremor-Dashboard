import connector

print(connector.ambulatory_collection.find_one())

# subject_ids = list(set(map(lambda subject: subject["subject_id"], connector.ambulatory_collection.find())))

# for subject_id in subject_ids:
    
    # records = connector.ambulatory_collection_acc.find({"subject_id": subject_id})
    
    # print("Records for subject", subject_id, connector.ambulatory_collection_acc.count_documents({"subject_id": subject_id}))
    # for record in records:
    #     print(record)
    
# test_record = connector.ambulatory_collection_acc.find_one()
# print(test_record)