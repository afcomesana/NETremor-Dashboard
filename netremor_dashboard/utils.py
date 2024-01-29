import re
import random
import string
import unicodedata

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
