import django.db.models
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.db.models import Count

from django_ace import AceWidget
from nested_inlines.admin import NestedModelAdmin,NestedTabularInline, NestedStackedInline
import forms_builder

from crowdataapp import models

class FieldAdmin(NestedTabularInline):
    model = forms_builder.forms.models.Field
    exclude = ('slug', )

class DocumentSetFormInline(NestedStackedInline):
    fields = ("title", "intro", "button_text", "response")
    model = models.DocumentSetForm
    inlines = [FieldAdmin]
    show_url = False

class DocumentSetAdmin(NestedModelAdmin):
    formfield_overrides = {
        django.db.models.TextField: {'widget': AceWidget(mode='javascript') },
    }

    def document_count(self, obj):
        return obj.document_set.count()

    list_display = ('name', 'document_count')
    inlines = [DocumentSetFormInline]

class DocumentUserFormEntryInline(admin.TabularInline):
    fields = ('user', 'answers')
    readonly_fields = ('user', 'answers')
    model = models.DocumentUserFormEntry

    def answers(self, obj):
        rv = '<ul>'
        form_fields = obj.form_entry.form.fields.all()
        for f, e in zip(form_fields, obj.form_entry.fields.all()):
            rv += "<li>%s: <strong>%s</strong></li>" % (f, e.value)
        rv += '</ul>'
        return mark_safe(rv)

class DocumentAdmin(admin.ModelAdmin):

    def queryset(self, request):
        return models.Document.objects.annotate(entries_count=Count('entries'))

    list_display = ('name', 'entries_count', 'document_set')
    list_filter = ('document_set__name',)
    inlines = [DocumentUserFormEntryInline]

    def entries_count(self, doc):
        return doc.entries_count
    entries_count.admin_order_field = 'entries_count'



admin.site.register(models.DocumentSet, DocumentSetAdmin)
admin.site.register(models.Document, DocumentAdmin)
