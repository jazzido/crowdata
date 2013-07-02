import re
from urlparse import urlparse

from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.dispatch import receiver
from django.core.urlresolvers import resolve

from annoying.decorators import render_to
from forms_builder.forms.signals import form_valid, form_invalid

from crowdataapp import models

@receiver(form_valid)
def create_entry(sender=None, form=None, entry=None, **kwargs):
    # get the document_id for this entry by the referrer
    # hacky, but it works
    try:
        document_id = resolve(urlparse(sender.META['HTTP_REFERER']).path).kwargs['document_id']
        models.DocumentUserFormEntry.objects.create(user=sender.user,
                                                    form_entry=entry,
                                                    document_id=document_id)
    except:
        # should probably delete the 'entry' here
        pass

@receiver(form_invalid)
def invalid_entry(sender=None, form=None, **kwargs):
    print repr(form.errors)

@render_to('transcription_new.html')
def transcription_new(request, document_id):
    document = get_object_or_404(models.Document, pk=document_id)
    document_embed_url = re.match(r'^(.+)\.html$', document.url).group(1) + '.js'

    return {
        'document': document,
        'document_embed_url': document_embed_url
    }
