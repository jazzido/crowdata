from urlparse import urlparse

from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.dispatch import receiver
from django.core.urlresolvers import resolve, reverse
from django.db.models import Count
from django.template import RequestContext

from annoying.decorators import render_to
from forms_builder.forms.signals import form_valid, form_invalid
from forms_builder.forms.forms import FormForForm

from crowdataapp import models

@receiver(form_valid)
def create_entry(sender=None, form=None, entry=None, **kwargs):
    # get the document_id for this entry from the referrer
    # hacky, but it works

    try:
        document_id = resolve(urlparse(sender.META['HTTP_REFERER']).path).kwargs['document_id']
        entry.document = models.Document.objects.get(pk=document_id)
        entry.user = sender.user
        entry.save()
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

class DocumentSetFormForForm(FormForForm):
    field_entry_model = models.DocumentSetFieldEntry

    class Meta:
        model = models.DocumentSetFormEntry
        exclude = ("form", "entry_time")


def form_detail(request, slug, template="forms/form_detail.html"):
    form = get_object_or_404(models.DocumentSetForm, slug=slug)
    request_context = RequestContext(request)
    args = (form, request_context, request.POST or None)

    form_for_form = DocumentSetFormForForm(*args)

    if request.method == 'POST':
        if not form_for_form.is_valid():
            form_invalid.send(sender=request, form=form_for_form)
        else:
            entry = form_for_form.save()
            form_valid.send(sender=request, form=form_for_form, entry=entry)
            return redirect(reverse('form_sent', kwargs={"slug": form.slug}))
    return render_to_response(template, { 'form': form }, request_context)

@render_to('transcription_new.html')
def transcription_new(request, document_set, document_id):
    document = get_object_or_404(models.Document,
                                 pk=document_id,
                                 document_set__slug=document_set)

    return {
        'document': document,
    }
