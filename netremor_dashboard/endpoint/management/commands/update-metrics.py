from django.core.management.base import BaseCommand, CommandError, CommandParser
from endpoint.utils import update_bradykinesia_metrics

class Command(BaseCommand):
    """
    For writting to console:
    - self.stdout.write(message, ending)
    - self.stderr.write(message, ending)

    Args:
        BaseCommand (_type_): _description_

    Returns:
        _type_: _description_
    """
    help = "Updates metrics for the specified disease."
    
    def add_arguments(self, parser):
        parser.add_argument("diseases", nargs="+", type=str)
    
    def handle(self, *args, **options):
        
        for disease in options["diseases"]:
            
            if disease == "bradykinesia":
                update_bradykinesia_metrics()
                
            else:
                self.stdout.write("'%s' is not supported yet" % disease, ending="\n\n")