from django.contrib import admin

# Register your models here.
from endpoint.models import Subject, Record, DataFile, Verification


# class SubjectAdmin(admin.ModelAdmin):
#     # fields = ["dominant_hand"]
#     list_display = ["name", "birth_year"]
#     fieldsets = [
#         (None, {"fields": ["name"]}),
#         ("Fechas", {"fields": ["birth_year", "illness_start_year"]})
#     ]
    
#     list_filter = ["birth_year"]
#     search_fields = ["name"]

# admin.site.register(Subject, SubjectAdmin)

admin.site.register(Subject)
admin.site.register(Record)
admin.site.register(DataFile)
admin.site.register(Verification)