# coding: utf-8
from urlparse import urlparse

from django.dispatch import receiver
from django.core.urlresolvers import resolve

from forms_builder.forms.signals import form_valid, form_invalid

from crowdataapp import models

@receiver(form_valid)
def create_entry(sender=None, form=None, entry=None, document_id=None, **kwargs):

    request = sender

    if not request.user.is_authenticated() or document_id is None:
        raise

    # get the document_id from the session
    # we don't want to pass around in clear view
    # the document_id this entry belongs to
    try:
        entry.document = models.Document.objects.get(pk=document_id)
        entry.user = request.user
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
