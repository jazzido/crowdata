from django.db import models
from django.utils.translation import ugettext_lazy as _
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
}
"""

class DocumentSet(models.Model):

    name = models.CharField(_('Document set name'), max_length='128',)
    slug = django_extensions_fields.AutoSlugField(populate_from=('name'))
    template_function = models.TextField(default=DEFAULT_TEMPLATE_JS,
                                         null=False,
                                         help_text=_('Javascript function to insert the document into the DOM. Receives the URL of the document as its only parameter. Must be called insertDocument'))
    entries_threshold = models.IntegerField(default=3,
                                            null=False,
                                            help_text=_('Maximum number of times the each document will be shown to users.'))

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _('Document Set')
        verbose_name_plural = _('Document Sets')

class DocumentSetForm(forms_builder.forms.models.Form):
    document_set = models.ForeignKey(DocumentSet, unique=True, related_name='form')

class Document(models.Model):
    name = models.CharField(max_length=256, editable=True, null=True)
    url = models.URLField(max_length='512', editable=True)
    document_set = models.ForeignKey(DocumentSet)

    def __unicode__(self):
        return "%s (%s)" % (self.name, self.url) if self.name else self.url

    def get_absolute_url(self):
        return reverse('crowdataapp.views.transcription_new',
                       args=[self.document_set.slug, self.pk])

    class Meta:
        verbose_name = _('Document')
        verbose_name_plural = _('Documents')

class DocumentUserFormEntry(models.Model):
    user = models.ForeignKey(User, null=True)
    form_entry = models.ForeignKey(forms_builder.forms.models.FormEntry)
    document = models.ForeignKey(Document, related_name='entries')

    def entry_to_json(self):
        return 'caca'
