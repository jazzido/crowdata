# coding: utf-8
import csv, sys, re, json
from datetime import datetime
import django.db.models
import django.http
from django.utils.translation import ugettext, ugettext_lazy as _
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.db.models import Count
from django.db import transaction
from django.conf.urls import patterns, url
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.forms import TextInput
from django.views.decorators.csrf import csrf_exempt

from django_ace import AceWidget
from nested_inlines.admin import NestedModelAdmin,NestedTabularInline, NestedStackedInline
import forms_builder

from crowdataapp import models

class DocumentSetFormFieldAdmin(NestedTabularInline):
    model = models.DocumentSetFormField
    exclude = ('slug', )
    extra = 1

class DocumentSetFormInline(NestedStackedInline):
    fields = ("title", "intro", "button_text")
    model = models.DocumentSetForm
    inlines = [DocumentSetFormFieldAdmin]
    show_url = False

class DocumentSetRankingDefinitionInline(NestedTabularInline):
    fields = ('name', 'label_field', 'magnitude_field', 'grouping_function', 'sort_order')
    model = models.DocumentSetRankingDefinition
    max_num = 2

    LABEL_TYPES = (
        forms_builder.forms.fields.TEXT,
        forms_builder.forms.fields.SELECT,
        forms_builder.forms.fields.RADIO_MULTIPLE,
    )

    MAGNITUDE_TYPES = (
        forms_builder.forms.fields.NUMBER,
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # this sucks
        document_set_id = int(re.search('documentset/(\d+)', request.path).groups()[0])
        document_set = models.DocumentSet.objects.get(pk=document_set_id)
        qs = models.DocumentSetFormField.objects.filter(form__document_set=document_set)

        if db_field.name == 'label_field':
            # get fields from this document_set form that can only act as labels
            kwargs["queryset"] = qs.filter(field_type__in=self.LABEL_TYPES, verify=True)
        elif db_field.name == 'magnitude_field':
            # get fields from this document_set form that can only act as magnitudes
            kwargs["queryset"] = qs.filter(field_type__in=self.MAGNITUDE_TYPES, verify=True)
        return super(DocumentSetRankingDefinitionInline, self) \
            .formfield_for_foreignkey(db_field, request, **kwargs)

class DocumentSetAdmin(NestedModelAdmin):

    class Media:
        css = {
            'all': ('admin/css/document_set_admin.css', )
        }
        js = ('admin/js/document_set_admin.js',)

    list_display = ('name', 'document_count', 'admin_links')
    fieldsets = (
        (_('Document Set Description'), {
            'fields': ('name', 'description')
        }),
        (_('Document Set Behaviour'), {
            'fields': ('entries_threshold', 'template_function', 'head_html')
        })
    )
    inlines = ()

    def change_view(self, request, object_id, form_url='', extra_context=None):
        self.inlines = (DocumentSetFormInline, DocumentSetRankingDefinitionInline, )
        return super(DocumentSetAdmin, self).change_view(request, object_id)

    def add_view(self, request, form_url='', extra_context=None):
        self.inlines = (DocumentSetFormInline,)
        return super(DocumentSetAdmin, self).add_view(request)

    def get_urls(self):
        urls = super(DocumentSetAdmin, self).get_urls()
        extra_urls = patterns('',
                              url('^(?P<document_set_id>\d+)/answers/$',
                                  self.admin_site.admin_view(self.answers_view),
                                  name="document_set_answers_csv"),
                              url('^(?P<document_set_id>\d+)/add_documents/$',
                                  self.admin_site.admin_view(self.add_documents_view),
                                  name='document_set_add_documents')
                             )
        return extra_urls + urls

    def add_documents_view(self, request, document_set_id):
        """ add a bunch of documents to a DocumentSet by uploading a CSV """
        document_set = get_object_or_404(self.model, pk=document_set_id)
        if request.FILES.get('csv_file'):
            # got a CSV, process, check and create
            csvreader = csv.reader(request.FILES.get('csv_file'))

            header_row = csvreader.next()
            if [h.strip() for h in header_row] != ['document_title', 'document_url']:
                messages.error(request,
                               _('Header cells must be document_title and document_url'))


            count = 0
            try:
                with transaction.commit_on_success():
                    for row in csvreader:
                        document_set.documents.create(name=row[0].strip(),
                                                      url=row[1].strip())
                        count += 1
            except:
                messages.error(request,
                               _('Could not create documents'))

                return redirect(reverse('admin:document_set_add_documents',
                                        args=(document_set_id,)))

            messages.info(request,
                          _('Successfully created %(count)d documents') % { 'count': count })

            return redirect(reverse('admin:crowdataapp_documentset_changelist'))

        else:
            return render_to_response('admin/document_set_add_documents.html',
                                      {
                                          'document_set': document_set,
                                          'current_app': self.admin_site.name,
                                      },
                                      RequestContext(request))

    def answers_view(self, request, document_set_id):
        document_set = get_object_or_404(self.model, pk=document_set_id)
        response = django.http.HttpResponse(mimetype="text/csv")
        writer = csv.DictWriter(response, fieldnames=[fn.encode('utf8')
                                                      for fn in document_set.field_names()])

        writer.writeheader()

        for entry in models.DocumentSetFormEntry.objects.filter(document__in=document_set.documents.all()):
            writer.writerow(self._encode_dict_for_csv(entry.to_dict()))

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
        l = '<a href="%s?document_set__id=%s">%s</a>' % (reverse("admin:crowdataapp_document_changelist"),
                                                           obj.pk,
                                                           obj.documents.count())
        return mark_safe(l)


class DocumentSetFormEntryInline(admin.TabularInline):
    fields = ('user_link', 'answers', 'entry_time')
    readonly_fields = ('user_link', 'answers', 'entry_time')
    list_select_related = True
    model = models.DocumentSetFormEntry
    extra = 0

    def answers(self, obj):
        field_template = "<li><input type=\"checkbox\" data-field-entry=\"%d\" data-document=\"%d\" data-entry-value=\"%s\" %s><span class=\"%s\">%s</span>: <strong>%s</strong></li>"
        print field_template
        rv = '<ul>'
        form_fields = obj.form.fields.all()
        rv += ''.join([field_template % (e.pk,
                                         obj.document.pk,
                                         e.value,
                                         'checked' if e.verified else '',
                                         'verify' if f.verify else '',
                                         f.label,
                                         e.value)
                       for f, e in zip(form_fields,
                                       obj.fields.all())])
        rv += '</ul>'

        return mark_safe(rv)


    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=(obj.user.id,))
        return mark_safe('<a href="%s">%s</a>' % (url, obj.user))


class DocumentAdmin(admin.ModelAdmin):

    class Media:
        css = {
            'all': ('admin/css/document_admin.css', )
        }
        js = ('admin/js/jquery-2.0.3.min.js', 'admin/js/nested.js', 'admin/js/document_admin.js',)

    fields = ('name', 'url', 'document_set_link', 'verified')
    readonly_fields = ('document_set_link','verified')
    list_display = ('name', 'verified', 'entries_count', 'document_set')
    list_filter = ('document_set__name',)
    inlines = [DocumentSetFormEntryInline]

    def queryset(self, request):
        return models.Document.objects.annotate(entries_count=Count('form_entries'))

    def get_urls(self):
        urls = super(DocumentAdmin, self).get_urls()
        my_urls = patterns('',
                           (r'^(?P<document>\d+)/document_set_field_entry/(?P<document_set_field_entry>\d+)/$',
                            self.admin_site.admin_view(self.field_entry_set))
        )
        return my_urls + urls

    def field_entry_set(self, request, document, document_set_field_entry):
        """ Set verify status for form field entries """
        if request.method != 'POST':
            return django.http.HttpResponseBadRequest()

        document = get_object_or_404(models.Document, pk=document)
        this_field_entry = get_object_or_404(models.DocumentSetFieldEntry, pk=document_set_field_entry)

        # get all answers for the same document that match with this one
        coincidental_field_entries = models.DocumentSetFieldEntry.objects.filter(field_id=this_field_entry.field_id,
                                                                                 value=this_field_entry.value,
                                                                                 entry__document=this_field_entry.entry.document)

        # set the verified state for all the matching answers
        for fe in coincidental_field_entries:
            fe.verified = (request.POST['verified'] == 'true')
            fe.save()

        # if there are verified answers for every field that's marked as 'verify'
        # set this Document as verified
        verified_fields = models.DocumentSetFormField \
                                .objects \
                                .filter(pk__in=set(map(lambda fe: fe.field_id,
                                                       models.DocumentSetFieldEntry.objects.filter(entry__document=this_field_entry.entry.document,
                                                                                                   verified=True))),
                                        verify=True,
                                        form=this_field_entry.entry.form)

        document.verified = (len(verified_fields) == len(models.DocumentSetFormField.objects.filter(verify=True,
                                                                                                    form=this_field_entry.entry.form)))

        document.save()

        return django.http.HttpResponse(json.dumps(map(lambda fe: fe.pk,
                                                       coincidental_field_entries)),
                                                   content_type="application/json")


    def document_set_link(self, obj):
        # crowdataapp_documentset_change
        change_url = reverse('admin:crowdataapp_documentset_change', args=(obj.document_set.id,))
        return mark_safe('<a href="%s">%s</a>' % (change_url, obj.document_set.name))
    document_set_link.short_description = _('Document Set')

    def entries_count(self, doc):
        return doc.entries_count
    entries_count.admin_order_field = 'entries_count'


admin.site.register(models.DocumentSet, DocumentSetAdmin)
admin.site.register(models.Document, DocumentAdmin)
admin.site.unregister(forms_builder.forms.models.Form)

from django.contrib.sites.models import Site
admin.site.unregister(Site)
