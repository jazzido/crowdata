import django.db.models
from django.contrib import admin

from django_ace import AceWidget
import forms_builder

from crowdataapp import models

class DocumentInline(admin.TabularInline):
    model = models.Document

class DocumentAdmin(admin.ModelAdmin):
    def entries_count(self, obj):
        return obj.entries.count()

    list_display = ('name', 'entries_count', 'document_set')
    list_filter = ('document_set__name',)

class DocumentUserFormEntriesInline(admin.TabularInline):
    pass

class DocumentSetAdmin(admin.ModelAdmin):
    formfield_overrides = {
        django.db.models.TextField: {'widget': AceWidget(mode='javascript') },
    }

    def document_count(self, obj):
        return obj.document_set.count()

    list_display = ('name', 'document_count')
    inlines = [DocumentInline]

admin.site.register(models.DocumentSet, DocumentSetAdmin)
admin.site.register(models.Document, DocumentAdmin)
