from endpoint.models import Subject, Record, Task, Datafile, Datafile_task_rel, Bradykinesia_metrics
import functools
import itertools

def save_subject(post_fields):
    # Save/update subject in database:
    if "id" not in post_fields.keys():
        raise KeyError("Subject ID must be provided.")
    
    try:
        subject = Subject(
            **{
                field.name:
                    post_fields[field.name] if field.name in post_fields else None for field in Subject._meta.fields
            }
        )
        
        if subject.dominant_hand not in get_choices_keys(Subject.DOMINANT_HAND_CHOICES):
            subject.dominant_hand = None
            
        if subject.gender not in get_choices_keys(Subject.GENDER_CHOICES):
            subject.gender = None
            
        if isinstance(subject.diagnosis, str) and not subject.diagnosis.strip():
            subject.diagnosis = None 

        subject.save()
        
    except KeyError as e:
        raise KeyError("Missing field in incoming request %s" % e)
    
    return subject
    
    
def get_choices_keys(choices):
    """
    Get the keys of the choices of a Model class from Django.
    
    :param choices: list of tuples passed as argument to the choices parameter field definition

    :return list[str] the keys of the choices
    """
    return list(map(lambda choice: choice[0], choices))


def update_bradykinesia_metrics():
    """
    The metrics used for the estimation of a patient's having bradykinsea on a given task are the followings:
    - Healty subjects mean time performing that task.
    - Healthy subjects maximum time performing that task.
    - Healthy subjects fundamental frequency performing that task.
    - Healthy subjects power of the fundamental frequency performing that task.
    
    To compute these values, the following process is followed:
    
    1. Get all the healthy subjects from the database.
    
    2. For each healthy subject, get all the tasks recorded.
    
    3. For each task, compute and store the following values:
    3. a. Time elapsed (seconds)
    3. b. Fundamental frequency
    3. c. Power of the fundamental frequency
    
    4. Once these values have been computed for every task for every subject, compute the following values
    and store them in the database:
    4. a. Maximum time elapsed performing a task.
    4. b. Medium time elapsed performing a task.
    4. c. Medium fundamental frequency performing a task.
    4. d. Medium power of the fundamental frequency performing a task.
    """
    
    # 1. Get all the healthy subjects from the database.
    healthy_subjects = Subject.objects.filter(diagnosis__isnull=True)
    
    # Get all the ambulatory records from all the healthy subjects
    records = functools.reduce(lambda a, b: a + b, map(lambda subject: list(subject.record_set.filter(type="ambulatory")),healthy_subjects))
    
    # Get all the tasks that whose metrics are going to be computed (those
    # that are stored and belong to one of the selected ambulatory records):
    recorded_tasks = Datafile_task_rel.objects.filter(record__in=records).values("task", "datafile").order_by("task")
    recorded_tasks = itertools.groupby(recorded_tasks, key=lambda task: task["task"])
    
    # Organize tasks to store their metrics ( tasks = [{task:"task_id", datafiles: [1,2,3]}, ...] )
    tasks = []
    for task_id, group in recorded_tasks:
        tasks += [{
            "task": task_id,
            "datafiles": functools.reduce(lambda acc, item: acc + [item["datafile"]], group, [])
        }]
