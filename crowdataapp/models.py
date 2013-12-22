from collections import defaultdict
from itertools import ifilter

from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models import Count

from django_extensions.db import fields as django_extensions_fields
from django_countries import CountryField
import forms_builder
import forms_builder.forms.fields
import forms_builder.forms.models

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

class UserProfile(models.Model):
    user = models.ForeignKey(User, unique=True)
    name = models.CharField(_('Your Name'), max_length='128', null=False, blank=False)
    country = CountryField(_('Your country'), null=True)
    show_in_leaderboard = models.BooleanField(_("Appear in the leaderboards"),
                                              default=True,
                                              help_text=_("If checked, you will appear in CrowData's leaderboards"))


class DocumentSet(models.Model):

    name = models.CharField(_('Document set name'), max_length='128',)

    description = models.TextField(null=True,
                                   blank=True,
                                   help_text=_('Description for this Document Set'))

    slug = django_extensions_fields.AutoSlugField(populate_from=('name'))
    template_function = models.TextField(default=DEFAULT_TEMPLATE_JS,
                                         null=False,
                                         help_text=_('Javascript function to insert the document into the DOM. Receives the URL of the document as its only parameter. Must be called insertDocument'))
    entries_threshold = models.IntegerField(default=3,
                                            null=False,
                                            help_text=_('Minimum number of coincidental answers for a field before marking it as valid'))

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

    def get_absolute_url(self):
        return reverse('crowdataapp.views.document_set_view',
                       args=[self.slug])

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
        return self.documents.filter(verified=False)

    def get_verified_documents(self):
        return self.documents.filter(verified=True)


    def leaderboard(self):
        """ Returns a queryset of the biggest contributors (User) to this DocumentSet """
        return User.objects.filter(documentsetformentry__form__document_set=self).annotate(num_entries=Count('documentsetformentry'))


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
    verify = models.BooleanField(_("Verify"), default=True)

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

    def get_answer_for_field(self, field):
        return self.fields.filter(field_id=field.pk)[0].value


class DocumentSetFieldEntry(forms_builder.forms.models.AbstractFieldEntry):
    entry = models.ForeignKey("DocumentSetFormEntry", related_name="fields")
    verified = models.BooleanField(default=False, null=False)

class DocumentSetRankingDefinition(models.Model):
    """ the definition of a ranking (leaderboard of sorts) for a DocumentSet """

    GROUPING_FUNCTIONS = (
        ('AVG', _('Average')),
        ('COUNT', _('Count')),
        ('SUM', _('Sum')),
    )

    name = models.CharField(_('Ranking title'), max_length=256, editable=True, null=False)
    document_set = models.ForeignKey(DocumentSet, related_name='rankings')
    label_field = models.ForeignKey(DocumentSetFormField, related_name='label_fields')
    magnitude_field = models.ForeignKey(DocumentSetFormField,
                                        related_name='magnitude_fields',
                                        null=True, blank=True)
    grouping_function = models.CharField(_('Grouping Function'),
                                         max_length=10,
                                         choices=GROUPING_FUNCTIONS,
                                         default='SUM')
    sort_order = models.BooleanField(_('Sort order'),
                                     default=False,
                                     help_text=_('Ascending if checked, descending otherwise'))


    def calculate(self):
        verified_answers = [doc.verified_answers()
                            for doc in self.document_set.documents.filter(verified=True)]
        rank = defaultdict(list)

        for answer in verified_answers:
            field = next(ifilter(lambda f: f == self.label_field,
                                 answer.keys()),
                         None)

            if field is None:
                continue

            label_field_value = answer.get(field)
            magnitude_field_value = answer.get(self.magnitude_field)

            if label_field_value is not None and magnitude_field_value is not None:
                rank[label_field_value].append(magnitude_field_value)


        if self.grouping_function == 'COUNT':
            mapper = lambda p: (p[0], len(p[1]))
        elif self.grouping_function == 'SUM':
            mapper = lambda p: (p[0], sum(map(float, p[1])))
        elif self.grouping_function == 'AVG':
            mapper = lambda p: (p[0],
                                sum(map(float, p[1])) / float(len(p[1])))

        return sorted(map(mapper,
                          rank.iteritems()),
                      key=lambda i: i[1], reverse=(not self.sort_order))

class Document(models.Model):
    name = models.CharField(_('Document title'), max_length=256, editable=True, null=True)
    url = models.URLField(_('Document URL'), max_length='512', editable=True)
    document_set = models.ForeignKey(DocumentSet, related_name='documents')
    verified = models.BooleanField(_('Verified'),
                                   help_text=_('Is this document verified?'))

    entries_threshold_override = models.IntegerField(null=True,
                                                     blank=True,
                                                     help_text=_('Minimum number of coincidental answers for a field before marking it as valid. Overrides the default value set in the Document Set this Document belongs to'))

    def __unicode__(self):
        return "%s (%s)" % (self.name, self.url) if self.name else self.url

    def get_absolute_url(self):
        return reverse('crowdataapp.views.transcription_new',
                       args=[self.document_set.slug, self.pk])


    def entries_threshold(self):
        if self.entries_threshold_override is None:
            return self.document_set.entries_threshold
        else:
            return self.entries_threshold_override


    def verified_answers(self):
        """ get a dict of verified answers (entries) for this Document
              { <DocumentSetFormField>: <value>, ... }
        """
        if not self.verified:
            return {}

        verified_answers = {}
        for form_entry in self.form_entries.all():
            verified_answers.update({field: value
                                      for (field, value) in [(DocumentSetFormField.objects.get(id=entry.field_id),
                                                              entry.value) for entry in form_entry.fields.filter(verified=True)]})

        return verified_answers

    def verify(self):
        # almost direct port from ProPublica's Transcribable.
        # Thanks @ashaw! :)

        form_entries = self.form_entries.all()
        form_fields = self.document_set.form.all()[0].fields.filter(verify=True)
        aggregate = defaultdict(dict)
        for field in form_fields:
            aggregate[field] = defaultdict(lambda: 0)

        for fe in form_entries:
            for field in form_fields:
                aggregate[field][fe.get_answer_for_field(field)] += 1

        chosen = {}
        for field, answers in aggregate.items():
            for answer, answer_ct in answers.items():
                if answer_ct > self.entries_threshold:
                    chosen[field] = max(answers.items(), lambda i: i[1])[0]


        if len(chosen.keys()) == len(form_fields):
            for field, verified_answer in chosen:
                DocumentSetFieldEntry.objects.filter(entry__in=form_entries,
                                                     field_id=f.pk,
                                                     value=verified_answer) \
                                             .update(verified=True)
            self.verified = True
        else:
            self.verified = False

        self.save()


    def unverify(self):
        DocumentSetFieldEntry.objects.filter(entry__in=self.form_entries.all()) \
                                     .update(verified=False)
        self.verified = False
        self.save()


    class Meta:
        verbose_name = _('Document')
        verbose_name_plural = _('Documents')
