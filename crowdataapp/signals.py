# coding: utf-8
from urlparse import urlparse

from django.dispatch import receiver
from django.core.urlresolvers import resolve

from forms_builder.forms.signals import form_valid, form_invalid

from crowdataapp import models

@receiver(form_valid)
def create_entry(sender=None, form=None, entry=None, **kwargs):
    # get the document_id for this entry from the referrer
    # hacky, but it works

    try:
        document_id = resolve(urlparse(sender.META['HTTP_REFERER']).path).kwargs['document_id']
        entry.document = models.Document.objects.get(pk=document_id)

        if sender.user.is_authenticated():
            entry.user = sender.user
        entry.save()

        # stored_validity_rate is a Decimal, need to convert float to str for storing
        entry.document.stored_validity_rate = str(entry.document.validity_rate())
        entry.document.save()

    except:
        # should probably delete the 'entry' here
        entry.delete()
        raise

@receiver(form_invalid)
def invalid_entry(sender=None, form=None, **kwargs):
    print repr(form.errors)
