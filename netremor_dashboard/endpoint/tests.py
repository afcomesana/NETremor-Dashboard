from django.test import TestCase
from .models import Subject, Record, Task, Datafile, Datafile_task_rel
from utils import get_random_string, measure_time
from django.conf import settings
import random
import pymongo
from datetime import datetime
import itertools
import pprint

class DatabasePerformancesTest(TestCase):
    
    def setUp(self):
        """
        Prepare the database for the query tests.
        1. Insert the tasks that are going to be performed.
        2. Insert specified number of users.
        3. For each user, insert specified number of ambulatory records.
        4. For each ambulatory record, insert specified number of tasks.
        """

        self.init_mongo_db()
        
        ###############
        # TEST PARAMS
        ###############
        
        SUBJECTS_NUMBER                = 10
        AMBULATORY_RECORDS_PER_SUBJECT = 2
        TASKS_PER_AMBULATORY_RECORD    = 5
        TRIALS_NUMBER                  = 1
        
        self.test_filename = "test-%s.csv" % SUBJECTS_NUMBER
        
        
        ######################################################
        # 1. Insert the tasks that are going to be performed.
        ######################################################
        for _ in range(TASKS_PER_AMBULATORY_RECORD):
            Task(id = get_random_string(2).upper(), name = get_random_string(random.randint(4,9))).save()
            # Does not have an analog process in MongoDB database
            

        #########################################
        # 2. Insert specified number of users.
        #########################################
        for _ in range(SUBJECTS_NUMBER):
            # Define random subject:
            subject = Subject(
                id                 = get_random_string(64),
                name               = " ".join([get_random_string(random.randint(5, 10)) for _ in range(3)]),
                gender             = Subject.GENDER_CHOICES[round(random.random())][0],
                birth_year         = random.randint(1900, 2010),
                illness_start_year = random.randint(1900, 2010),
                dominant_hand      = Subject.DOMINANT_HAND_CHOICES[round(random.random())][0],
            )
            
            if round(random.random()):
                subject.diagnosis = " ".join([get_random_string(random.randint(5, 10)) for i in range(random.randint(1, 9))])

            subject.save()
            # Does not have an analog process in MongoDB database

            #####################################################################
            # 3. For each user, insert specified number of ambulatory records.
            #####################################################################
            for _ in range(AMBULATORY_RECORDS_PER_SUBJECT):
                record = Record(subject=subject, type="ambulatory")
                record.save()
                # Does not have an analog process in MongoDB database
                
                # Initiliaze tasks array of MongoDB ambulatory_data collection documents
                mongo_db_tasks = []
                
                #####################################################################
                # 4. For each ambulatory record, insert specified number of tasks.
                #####################################################################
                for task in Task.objects.all():
                    
                    for trial in range(TRIALS_NUMBER):
                        
                        # Store datafile name for each sensor
                        trial_datafiles = {}
                        
                        # Create one datafile per sensor:
                        for sensor, _ in settings.SENSOR_CHOICES:
                            datafile = Datafile(record=record, name="%s.csv" % get_random_string(10), sensor=sensor)
                            datafile.save()
                            
                            # We will retrieve this name for inserting the info in the Mongo database
                            trial_datafiles[sensor] = datafile.name
                            
                            # Attach this data file to the curren task:
                            Datafile_task_rel(record=record, datafile= datafile, task=task, trial=trial).save()

                            
                        mongo_db_tasks += [{
                            "taskId": task.__dict__["id"],
                            "taskName": task.__dict__["name"],
                            "taskDescription": task.__dict__["description"],
                            "trial": trial,
                            "accelerometerFilename": trial_datafiles["accelerometer"],
                            "gyroscopeFilename": trial_datafiles["gyroscope"],
                        }]
                        
            
                # Insert each record in the MongoDB model
                mongo_subject = subject.__dict__.copy()
                mongo_subject["tasks"] = mongo_db_tasks
                mongo_subject["subject_id"] = mongo_subject["id"]
                mongo_subject["record_id"] = record.id
                mongo_subject["record_added_on"] = record.added_on.timestamp()
                del mongo_subject["id"]
                del mongo_subject["_state"]
                
                self.mongo_db["ambulatory_data"].insert_one(mongo_subject)
                
                
        random_record = Record.objects.all()[random.randint(0, AMBULATORY_RECORDS_PER_SUBJECT*SUBJECTS_NUMBER - 1)]
        
        self.random_subject_id = Subject.objects.all()[random.randint(0, SUBJECTS_NUMBER-1)].id
        self.random_record_id  = random_record.id
        self.random_task_id    = random_record.datafile_task_rel_set.all()[random.randint(0, TASKS_PER_AMBULATORY_RECORD-1)].task_id
        self.random_trial      = random.randint(0, TRIALS_NUMBER - 1)

    def test_get_subjects(self):
        """
        First test for comparing both database models performances:
        Get a list with all of the subjects in the database.
        - Subjects must be in the list only once.
        - The following fields are required: id, name, birth_year and diagnosis.
        """
        
        @measure_time(self.test_filename)
        def get_mysql_subjects():
            Subject.objects.values("id", "name", "birth_year", "diagnosis")
            
        @measure_time(self.test_filename)
        def get_mongo_subjects():
            subjects = self.mongo_db["ambulatory_data"].find({}, {"_id": 0, "subject_id": True, "birth_year": True, "name": True})
            subjects = {subject["subject_id"]: subject for subject in subjects if subject}.values()
            
            # TODO: Test this first selecting distinct subject_ids and then fetching data for each id
        
        get_mysql_subjects()
        get_mongo_subjects()
        
        
    def test_get_subject_records(self):
        """
        Given a subject, get all of its records.
        Records must be presented in an object with two keys:
        - continuous: Its id. <--- not applicable
        - ambulatory: List of the ambulatory records, including its id and creation date.
        """
        
        @measure_time(self.test_filename)
        def get_mysql_subject_records(subject_id):
            records = Record.objects.filter(subject_id=subject_id, type = "ambulatory").values("id", "added_on")

            
        @measure_time(self.test_filename)
        def get_mongo_subject_records(subject_id):
            records = list(self.mongo_db["ambulatory_data"].find({"subject_id": subject_id}, {"record_added_on": 1}))
            
        get_mysql_subject_records(self.random_subject_id)
        get_mongo_subject_records(self.random_subject_id)
        
    
    def test_get_tasks_in_ambulatory_record(self):
        """
        Given a record, get all of the tasks that have been performed in the record.
        Tasks must be presented in a list where each item has the following keys:
        - task: {id, name, description}
        - trials: [0, ..., n_trials]
        """
        
        @measure_time(self.test_filename)
        def get_mysql_ambulatory_record_tasks(record_id):
            # TODO: Test this query directly through a MySQL query, not django
            record_tasks = Record.objects.get(id=record_id).datafile_task_rel_set.values("task_id", "trial").distinct().order_by("task_id")
            tasks        = {}
    
            for task_id, group in itertools.groupby(record_tasks, lambda item: item["task_id"]):
                        
                tasks[task_id] = {
                    "task": Task.objects.get(id=task_id),
                    "trials": list(map(lambda item: item["trial"], group)), 
                }
                
            tasks = list(tasks.values())
            
            
        @measure_time(self.test_filename)
        def get_mongo_ambulatory_record_tasks(record_id):
            record_tasks = self.mongo_db["ambulatory_data"].find_one({"record_id": record_id}, {"_id": 0, "tasks": 1})
            record_tasks = sorted(record_tasks["tasks"], key=lambda item: item["taskId"])

            tasks = {}
    
            for task_id, group in itertools.groupby(record_tasks, lambda item: item["taskId"]):
                
                tasks[task_id] = {}
                
                for item in group:
                    tasks[task_id]["task"] = {
                        "id": item["taskId"],
                        "name": item["taskName"],
                        "description": item["taskDescription"],
                    }
                    
                    if "trials" in tasks[task_id].keys():
                        tasks[task_id]["trials"] += [item["trial"]]
                    
                    else:
                        tasks[task_id]["trials"] = [item["trial"]]
                
            tasks = list(tasks.values())
            
        # TODO: Another test to get the same as the above one but directly each sensor file
            
        get_mysql_ambulatory_record_tasks(self.random_record_id)
        get_mongo_ambulatory_record_tasks(self.random_record_id)
        
    def test_get_datafiles_by_task_and_trial(self):
        """
        Given an ambulatory record, find the data files corresponding to the given task and trial.
        Files must be returned in a list whose elements are dictionaries with the following keys:
        - sensor1: sensor1_datafile_name
        - sensor2: sensor2_datafile_name
        - ...
        - sensorN: sensorN_datafile_name
        """
        @measure_time(self.test_filename)
        def get_mysql_datafiles(record_id, task_id, trial):
            datafile_ids = Record.objects.get(id = record_id).datafile_task_rel_set.filter(task=task_id, trial=trial).values_list("datafile")
            
            datafiles = Datafile.objects.filter(pk__in = datafile_ids)
            datafiles = [{datafile.sensor: datafile.name} for datafile in datafiles]

        @measure_time(self.test_filename)    
        def get_mongo_datafiles(record_id, task_id, trial):
            pipeline = [
                {"$match": {"record_id": record_id}},
                {"$unwind": "$tasks"},
                {"$match": {"tasks.taskId": task_id, "tasks.trial": 0}}
            ]
            
            sensors = ["accelerometer", "gyroscope"]
            datafiles = []
            
            for recorded_task in self.mongo_db["ambulatory_data"].aggregate(pipeline):
                datafiles += [{sensor: recorded_task["tasks"]["%sFilename" % sensor]} for sensor in sensors]


        get_mysql_datafiles(self.random_record_id, self.random_task_id, self.random_trial)
        get_mongo_datafiles(self.random_record_id, self.random_task_id, self.random_trial)
            
  
            
    def init_mongo_db(self):
        database_name = "netremor_db"
        client = pymongo.MongoClient()
        client.drop_database(database_name)
                
        self.mongo_db = client[database_name]