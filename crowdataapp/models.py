from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models import Count


from django_extensions.db import fields as django_extensions_fields

import forms_builder

DEFAULT_TEMPLATE_JS = """// Javascript function to insert the document into the DOM.
// Receives the URL of the document as its only parameter.
// Must be called insertDocument
// JQuery is available
// resulting element should be inserted into div#document-viewer-container
function insertDocument(document_url) {
}
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

    description = models.TextField(null=True,
                                   help_text=_('Description for this Document Set'))

    slug = django_extensions_fields.AutoSlugField(populate_from=('name'))
    template_function = models.TextField(default=DEFAULT_TEMPLATE_JS,
                                         null=False,
                                         help_text=_('Javascript function to insert the document into the DOM. Receives the URL of the document as its only parameter. Must be called insertDocument'))
    entries_threshold = models.IntegerField(default=3,
                                            null=False,
                                            help_text=_('Maximum number of times each document will be shown to users.'))

    head_html = models.TextField(default='<!-- <script> or <link rel="stylesheet"> tags go here -->',
                                 null=True,
                                 help_text=_('HTML to be inserted in the <head> element in this page'))

    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)

    class Meta:
        verbose_name = _('Document Set')
        verbose_name_plural = _('Document Sets')

    def __unicode__(self):
        return self.name

    def admin_links(self):
        kw = {"args": (self.id,)}
        links = [
            (_("Export all answers to CSV"), reverse("admin:document_set_answers_csv", **kw)),
            (_("Add Documents to this document set"), reverse("admin:document_set_add_documents", **kw))
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

    def get_pending_documents(self):
        """
        DocumentSet.get_pending_documents(): returns a django.db.models.query.QuerySet, giving the document set's documents that were no already validated. Note that since it is a QuerySet it is possible to filter them later without an extra query.
        """

        # TODO Creo que esto esta mal. Deberia considerar el DocumentSetFormEntry en lugar del DocumentSetFieldEntry
        # q = """
        #     id IN
        #       (SELECT DISTINCT `id`
        #        FROM
        #          (SELECT `crowdataapp_document`.`id`,
        #                  ds_field_entry.`value`,
        #                  ds_field_entry.`field_id`,
        #                  COUNT(ds_field_entry.`value`) AS c
        #           FROM crowdataapp_document
        #           LEFT OUTER JOIN crowdataapp_documentsetformentry ds_form_entry ON (crowdataapp_document.id = ds_form_entry.document_id)
        #           LEFT OUTER JOIN crowdataapp_documentsetfieldentry ds_field_entry ON (ds_form_entry.id = ds_field_entry.entry_id)
        #           WHERE crowdataapp_document.document_set_id = %s
        #           GROUP BY ds_field_entry.`value`,
        #                    ds_field_entry.field_id,
        #                    crowdataapp_document.id) AS T
        #        GROUP BY field_id,
        #                 id HAVING max(c) < %s)
        #     """
        # return self.documents.extra(where=[q], params=[self.id, self.entries_threshold])

        return Document.objects.exclude(id__in=Document.objects.annotate(c=Count('form_entries'))
                                        .filter(document_set=self.id)
                                        .filter(c__gte=self.entries_threshold))

class DocumentSetForm(forms_builder.forms.models.AbstractForm):
    document_set = models.ForeignKey(DocumentSet, unique=True, related_name='form')
    #document_set = models.OneToOneField(DocumentSet, parent_link=True)

    def autocomplete_fields(self):
        """ Returns a list of every text field with autocompletion enabled """
        return self.fields.all()

    @models.permalink
    def get_absolute_url(self):
        return ('crowdata_form_detail', (), { 'slug': self.slug })

class DocumentSetFormField(forms_builder.forms.models.AbstractField):
    autocomplete = models.BooleanField(_("Autocomplete"),
        help_text=_("If checked, this text field will have autocompletion"))
    form = models.ForeignKey(DocumentSetForm, related_name="fields")
    order = models.IntegerField(_("Order"), null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.order is None:
            self.order = self.form.fields.count()
        super(DocumentSetFormField, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        fields_after = self.form.fields.filter(order__gte=self.order)
        fields_after.update(order=models.F("order") - 1)
        super(DocumentSetFormField, self).delete(*args, **kwargs)

class DocumentSetFormEntry(forms_builder.forms.models.AbstractFormEntry):
    """ A :class:`forms_builder.forms.models.AbstractFormEntry` plus
    foreign keys to the :class:`User` and filled the form and the
    :class:`Document` it belongs to
    """

    form = models.ForeignKey("DocumentSetForm", related_name='entries')
    document = models.ForeignKey('Document', related_name='form_entries', blank=True, null=True)
    user = models.ForeignKey(User, blank=True, null=True)

    def to_dict(self):
        form_fields = dict([(f.id, f.label)
                            for f in self.form.fields.all()])
        entry_time_name = forms_builder.forms.models.FormEntry._meta.get_field('entry_time').verbose_name.title()

        rv = dict()
        rv['user'] = str(self.user.pk)
        rv[Document._meta.get_field('name').verbose_name.title()] = self.document.name
        rv[Document._meta.get_field('url').verbose_name.title()] = self.document.url

        for field_entry in self.form_entry.fields.all():
            rv[form_fields[field_entry.field_id]] = field_entry.value

        rv[entry_time_name] = self.form_entry.entry_time

        return rv


class DocumentSetFieldEntry(forms_builder.forms.models.AbstractFieldEntry):
    entry = models.ForeignKey("DocumentSetFormEntry", related_name="fields")
    #field = models.ForeignKey("DocumentSetFormField", related_name="entry_fields")


class Document(models.Model):
    name = models.CharField(_('Document title'), max_length=256, editable=True, null=True)
    url = models.URLField(_('Document URL'), max_length='512', editable=True)
    document_set = models.ForeignKey(DocumentSet, related_name='documents')

    def __unicode__(self):
        return "%s (%s)" % (self.name, self.url) if self.name else self.url

    def get_absolute_url(self):
        return reverse('crowdataapp.views.transcription_new',
                       args=[self.document_set.slug, self.pk])

    def validity_rate(self):
        """
            Document.validity_rate(): a 0 to 1 rate which shows how much controversial (or difficult to read maybe) was the document, even if it is already considered validated. It is implemented as the avarage of the ratio of each field (defined as the number of matching responses / total responses).

            avg of validity per fields:
        """

        # TODO: find a more elegant solution, maybe in a sigle query.
        counts = [self.__field_validity_rate(field) for field in DocumentSetFormField.objects.filter(form__document_set=self.document_set)]
        return sum(counts)/len(counts)


    def __field_validity_rate(self, field):
        """
            Field: a DocumentSetFormEntry
        """

#         I think the elegant solution is this:
#         return DocumentSetFieldEntry.objects.values('value').annotate(c=Count('value')).filter(entry__document_id=self.id, field_id=field.id).order_by('c').aggregate(Avg('c'))
#         But it seams to be a bug in django models that results in this error: "DatabaseError: near "FROM": syntax error"
#         https://code.djangoproject.com/ticket/15624
#         That's that the non-so-efficient field_coincidences is called

        coincidence_count = self.__field_coincidences(field)
        fec = self.form_entries.count()
        return float(coincidence_count) / (fec if fec > 0 else 1)

    def __field_coincidences(self, field):
        """
            Returns how many times a same value for a field was given.
        """
        result = DocumentSetFieldEntry.objects.values('value').annotate(count=Count('value')).filter(entry__document=self, field_id=field.pk).order_by('-count')
        return result[0]['count'] if result else 0

    def validated(self):
        """
            Document.validated(): returns True if the document has at least the document set's threshold coincidental entries for each DocumentSetFormField. That way, if, for example, if threshold=3, and a field receives three different answers for the same field, it won't be considered validated, until it has three matching answers.

            True if each entry has more than the required threshold equal values; thus, the document was successfully crod scrapped.
            This is not right: is inconsistent with get_pending_documents, which interprets the threshold per entry.
        """
        threshold = self.document_set.entries_threshold
        return all([self.__field_coincidences(field) >= threshold for field in DocumentSetFormField.objects.filter(form__document_set_id=self.document_set.id)])

    def get_answer(self, key):
        """
            Document.get_answer(): takes and entry key (its slug) and return a tuple with: the most coincidental value, how many matching answers it has and its validity rate (defined as the number of matching responses / total responses).

            returns the most repeated value for a given field, it occurences and its validity rate in a tuple
        """
        max_field_count = DocumentSetFieldEntry.objects \
                .filter(entry__document=self, field__slug=key) \
                .values('value').annotate(count=Count('value')) \
                .order_by()[0]

        total_field_count = self.form_entries.count()
        return (max_field_count['value'], max_field_count['count'], float(max_field_count['count']) / self.form_entries.count())


    class Meta:
        verbose_name = _('Document')
        verbose_name_plural = _('Documents')
