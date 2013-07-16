import csv
from datetime import datetime

import django.db.models
import django.http
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.db.models import Count
from django.conf.urls import patterns, url
from django.shortcuts import get_object_or_404

from django_ace import AceWidget
from nested_inlines.admin import NestedModelAdmin,NestedTabularInline, NestedStackedInline
import forms_builder

from crowdataapp import models

class FieldAdmin(NestedTabularInline):
    model = models.DocumentSetFormField
    exclude = ('slug', )
    extra = 1

class DocumentSetFormInline(NestedStackedInline):
    fields = ("title", "intro", "button_text")
    model = models.DocumentSetForm
    inlines = [FieldAdmin]
    show_url = False


class DocumentSetAdmin(NestedModelAdmin):

    class Media:
        css = {
            'all': ('admin/css/document_set_admin.css', )
        }
        js = ('admin/js/document_set_admin.js',)

    formfield_overrides = {
        django.db.models.TextField: {'widget': AceWidget(mode='javascript') },
    }

    def get_urls(self):
        urls = super(DocumentSetAdmin, self).get_urls()
        extra_urls = patterns('',
                              url('^(?P<document_set_id>\d+)/answers/$',
                                  self.admin_site.admin_view(self.answers_view),
                                  name="document_set_answers_csv")
                             )
        return extra_urls + urls

    def answers_view(self, request, document_set_id):
        document_set = get_object_or_404(self.model, pk=document_set_id)
        response = django.http.HttpResponse(mimetype="text/csv")
        writer = csv.DictWriter(response, fieldnames=[fn.encode('utf8')
                                                      for fn in document_set.field_names()])

        writer.writeheader()

        # for entry in models.DocumentUserFormEntry.objects.filter(document__in=document_set.documents.all()):
        #     writer.writerow(self._encode_dict_for_csv(entry.to_dict()))

        return response

    def _encode_dict_for_csv(self, d):
        rv = {}
        for k,v in d.items():
            k = k.encode('utf8') if type(k) == unicode else k
            if type(v) == datetime:
                rv[k] = v.strftime('%Y-%m-%d %H:%M')
            elif type(v) == unicode:
                rv[k] = v.encode('utf8')
            else:
                rv[k] = v

        return rv

    def document_count(self, obj):
        print obj
        return obj.documents.count()

    list_display = ('name', 'document_count', 'admin_links')
    inlines = [DocumentSetFormInline]

class DocumentUserFormEntryInline(admin.TabularInline):
    fields = ('user', 'answers')
    readonly_fields = ('user', 'answers')
    model = models.DocumentSetFormEntry

    def answers(self, obj):
        rv = '<ul>'
        form_fields = obj.form_entry.form.fields.all()
        rv += ''.join(["<li>%s: %s</li>" % (f, e.value)
                       for f, e in zip(form_fields,
                                       obj.form_entry.fields.all())])
        rv += '</ul>'
        print 'caca'
        print rv

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
admin.site.unregister(forms_builder.forms.models.Form)
from django.contrib.sites.models import Site
admin.site.unregister(Site)
