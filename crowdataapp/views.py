import re
from urlparse import urlparse

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.dispatch import receiver
from django.core.urlresolvers import resolve
from django.db.models import Count

from annoying.decorators import render_to
from forms_builder.forms.signals import form_valid, form_invalid

from crowdataapp import models

@receiver(form_valid)
def create_entry(sender=None, form=None, entry=None, **kwargs):
    # get the document_id for this entry from the referrer
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

def redirect_to_new_transcription(request, document_set):
    doc_set = get_object_or_404(models.DocumentSet, slug=document_set)
    document_id = resolve(urlparse(request.META['HTTP_REFERER']).path).kwargs['document_id']
    print document_id

    candidates = models.Document \
                       .objects.annotate(entries_count=Count('entries')) \
                               .filter(document_set=doc_set,
                                       entries_count__lt=doc_set.entries_threshold) \
                               .exclude(pk=document_id)

    if candidates.count() == 0:
        # TODO What to do? What to do?
        pass
    else:
        return redirect(candidates.order_by('?')[0])

@render_to('transcription_new.html')
def transcription_new(request, document_set, document_id):
    document = get_object_or_404(models.Document,
                                 pk=document_id,
                                 document_set__slug=document_set)

    document_embed_url = re.match(r'^(.+)\.html$', document.url).group(1) + '.js'

    return {
        'document': document,
        'document_embed_url': document_embed_url
    }
