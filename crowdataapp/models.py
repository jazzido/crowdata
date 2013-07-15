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

# some mokeypatching, I don't want every field type to be available in forms
#from forms_builder.forms import fields

ALLOWED_FIELD_TYPES = (
    forms_builder.forms.fields.TEXT,
    forms_builder.forms.fields.TEXTAREA,
    forms_builder.forms.fields.CHECKBOX,
    forms_builder.forms.fields.CHECKBOX_MULTIPLE,
    forms_builder.forms.fields.SELECT,
    forms_builder.forms.fields.SELECT_MULTIPLE,
    forms_builder.forms.fields.DATE,
    forms_builder.forms.fields.DATE_TIME,
    forms_builder.forms.fields.HIDDEN,
    forms_builder.forms.fields.NUMBER,
    forms_builder.forms.fields.URL,
)

forms_builder.forms.models.Field._meta.local_fields[3]._choices \
    = filter(lambda i: i[0] in ALLOWED_FIELD_TYPES,
             forms_builder.forms.fields.NAMES)


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
        document_title_name = Document._meta.get_field('name').verbose_name.title()
        document_url_name = Document._meta.get_field('url').verbose_name.title()

        form = self.form.all()[0]
        return ['user'] \
            + [document_title_name, document_url_name] \
            + [f.label
               for f in form.fields.all()] \
            + [entry_time_name]


class DocumentSetForm(forms_builder.forms.models.Form):
    document_set = models.ForeignKey(DocumentSet, unique=True, related_name='form')

class DocumentSetFormField(forms_builder.forms.models.Field):
    autocomplete = models.BooleanField(_("Autocomplete"),
        help_text=_("If checked, this text field will have autocompletion"))

class Document(models.Model):
    name = models.CharField(_('Document title'), max_length=256, editable=True, null=True)
    url = models.URLField(_('Document URL'), max_length='512', editable=True)
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
        rv[Document._meta.get_field('name').verbose_name.title()] = self.document.name
        rv[Document._meta.get_field('url').verbose_name.title()] = self.document.url

        for field_entry in self.form_entry.fields.all():
            rv[form_fields[field_entry.field_id]] = field_entry.value

        rv[entry_time_name] = self.form_entry.entry_time

        return rv
