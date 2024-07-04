from typing import Any
from django.core.management.base import BaseCommand, CommandError
from endpoint.models import Record
from django.conf import settings

import utils
import endpoint.utils as endpoint

class Command(BaseCommand):
    utils.write_log("Executing process-files cron function", "cron")
    
    def handle(self, *args, **options):
        
        for record in Record.objects.filter(type="continuous"):
            endpoint.process_record_datafiles(record)