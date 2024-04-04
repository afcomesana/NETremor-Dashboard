from endpoint.models import Subject

def save_subject(post_fields):
    # Save/update subject in database:
    if "subject_id" not in post_fields.keys():
        raise KeyError("Subject ID must be provided.")
    
    post_fields["id"] = post_fields["subject_id"]
    del post_fields["subject_id"]
    
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
    
    Args:
    - choices: list of tuples passed as argument to the choices parameter field definition

    Return:
    - list[str] the keys of the choices
    """
    return list(map(lambda choice: choice[0], choices))