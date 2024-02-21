import re
import time
import random
import string
import unicodedata
import numpy as np

def str2filename(text):
    """
    Convert any string to a file-like format.
    
    :param text: to be converted
    
    :return str: file-like string
    
    """
    filename = text.strip().lower().replace(" ", "_")
    filename = re.sub(r'[^0-9a-z\_\.]', "", filename)
    filename = re.sub(r'[_]+', "_", filename)
    filename = re.sub(r'[\.]+', "_", filename)
    
    return filename

def normalize_text(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ASCII", "ignore")
    text = text.decode("ASCII")
    
    return text

def get_random_string(length):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def measure_time(filename):
    """Measure elapsed time for the function to execute

    Args:
        func (function): function whose execution time we want to measure
    """

    def decorator(func):

        def wrapper(*args, **kwargs):
            
            ITER_TIMES = 100
            times = []
            for _ in range(ITER_TIMES):
                start_time = time.time()
                
                func(*args)
                
                end_time = time.time()
                
                times += [end_time - start_time]
                
            
            
            with open(filename, "a") as file:
                file.write(";".join([func.__name__, str(np.mean(times))]))
                file.write("\n")
            print("Mean time for %s: %s" % (func.__name__, np.mean(times)))
            
        return wrapper
    return decorator