from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

from django_extensions.db import fields as django_extensions_fields
import forms_builder

class DocumentSet(models.Model):
    name = models.CharField(max_length='128')
    slug = django_extensions_fields.AutoSlugField(populate_from=('name'))
    form = models.ForeignKey(forms_builder.forms.models.Form, null=False)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _('Document Set')
        verbose_name_plural = _('Document Sets')

class Document(models.Model):
    name = models.CharField(max_length=256, editable=True, null=True)
    url = models.URLField(max_length='512', editable=True)
    document_set = models.ForeignKey(DocumentSet)

    def __unicode__(self):
        return "%s (%s)" % (self.name, self.url) if self.name else self.url

    class Meta:
        verbose_name = _('Document')
        verbose_name_plural = _('Documents')

class DocumentUserFormEntry(models.Model):
    user = models.ForeignKey(User)
    form_entry = models.ForeignKey(forms_builder.forms.models.FormEntry)
    document = models.ForeignKey(Document)
