from django.template.defaulttags import register
from utils import normalize_text

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def normalize(value):
    return normalize_text(value)

@register.filter
def make_range(value):
    return list(range(value))
