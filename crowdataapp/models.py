from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from django_extensions.db import fields as django_extensions_fields
import forms_builder

DEFAULT_TEMPLATE_JS = """
// Javascript function to insert the document into the DOM.
// Receives the URL of the document as its only parameter.
// Must be called insertDocument
// JQuery is available
// resulting element should be inserted into div#document-viewer-container
function insertDocument(document_url) {
o}
"""

class DocumentSet(models.Model):

    name = models.CharField(_('Document set name'), max_length='128',)
    slug = django_extensions_fields.AutoSlugField(populate_from=('name'))
    template_function = models.TextField(default=DEFAULT_TEMPLATE_JS,
                                         null=False,
                                         help_text=_('Javascript function to insert the document into the DOM. Receives the URL of the document as its only parameter. Must be called insertDocument'))
    entries_threshold = models.IntegerField(default=3,
                                            null=False,
                                            help_text=_('Maximum number of times each document will be shown to users.'))

    class Meta:
        verbose_name = _('Document Set')
        verbose_name_plural = _('Document Sets')

    def __unicode__(self):
        return self.name

    def admin_links(self):
        kw = {"args": (self.id,)}
        links = [
            (_("Export all answers to CSV"), reverse("admin:document_set_answers_csv", **kw)),
        ]
        for i, (text, url) in enumerate(links):
            links[i] = "<a href='%s'>%s</a>" % (url, ugettext(text))
        return "<br>".join(links)
    admin_links.allow_tags = True
    admin_links.short_description = ""

    def field_names(self):
        """Used for column names in CSV export of
        :class:`DocumentUserFormEntry`
        """

        entry_time_name = forms_builder.forms.models.FormEntry._meta.get_field('entry_time').verbose_name.title()

        form = self.form.all()[0]
        return ['user'] \
        + [f.label
           for f in form.fields.all()] \
        + [entry_time_name]



class DocumentSetForm(forms_builder.forms.models.Form):
    document_set = models.ForeignKey(DocumentSet, unique=True, related_name='form')

class Document(models.Model):
    name = models.CharField(max_length=256, editable=True, null=True)
    url = models.URLField(max_length='512', editable=True)
    document_set = models.ForeignKey(DocumentSet, related_name='documents')

    def __unicode__(self):
        return "%s (%s)" % (self.name, self.url) if self.name else self.url

    def get_absolute_url(self):
        return reverse('crowdataapp.views.transcription_new',
                       args=[self.document_set.slug, self.pk])

    class Meta:
        verbose_name = _('Document')
        verbose_name_plural = _('Documents')

class DocumentUserFormEntry(models.Model):
    """The answer (an instance of :class:`forms_builder.forms.models.FormEntry`)
    provided by a :class:`User` for a :class:`Document`
    """

    user = models.ForeignKey(User, null=True)
    form_entry = models.ForeignKey(forms_builder.forms.models.FormEntry)
    document = models.ForeignKey(Document, related_name='entries')

    def to_dict(self):
        form_fields = dict([(f.id, f.label)
                            for f in self.form_entry.form.fields.all()])
        entry_time_name = forms_builder.forms.models.FormEntry._meta.get_field('entry_time').verbose_name.title()

        rv = dict()
        rv['user'] = str(self.user.pk)

        for field_entry in self.form_entry.fields.all():
            rv[form_fields[field_entry.field_id]] = field_entry.value

        rv[entry_time_name] = self.form_entry.entry_time

        return rv
