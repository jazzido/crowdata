import django.db.models
from django.contrib import admin

from django_ace import AceWidget

from crowdataapp import models

class DocumentSetAdmin(admin.ModelAdmin):
    formfield_overrides = {
        django.db.models.TextField: {'widget': AceWidget(mode='javascript') },
    }

admin.site.register(models.DocumentSet, DocumentSetAdmin)
admin.site.register(models.Document)
