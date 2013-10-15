# coding: utf-8
from django.shortcuts import get_object_or_404, redirect, render_to_response

from django.core.urlresolvers import resolve, reverse
from django.db.models import Count
from django.db.models.signals import post_save
from django.template import RequestContext
from django.http import HttpResponse

from annoying.decorators import render_to
from forms_builder.forms.forms import FormForForm
from forms_builder.forms.signals import form_valid, form_invalid

from crowdataapp import models

@render_to('document_set_index.html')
def document_set_index(request):
    document_sets = models.DocumentSet.objects.order_by('-created_at')
    return { 'document_sets': document_sets }

@render_to('document_set_landing.html')
def document_set_view(request, document_set):
    return {
        'document_set': get_object_or_404(models.DocumentSet,
                                          slug=document_set)
    }

def redirect_to_new_transcription(request, document_set):
    doc_set = get_object_or_404(models.DocumentSet, slug=document_set)

    candidates = doc_set.get_pending_documents()

    if request.user.is_authenticated():
        candidates = candidates.exclude(form_entries__user=request.user)

    if candidates.count() == 0:
        # TODO Redirect to a message page: "you've gone through all the documents in this project!"
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
            return HttpResponse('') #redirect(reverse('form_sent', kwargs={"slug": form.slug}))
    return render_to_response(template, { 'form': form }, request_context)

@render_to('transcription_new.html')
def transcription_new(request, document_set, document_id):
    document = get_object_or_404(models.Document,
                                 pk=document_id,
                                 document_set__slug=document_set)

    return {
        'document': document,
        'head_html': document.document_set.head_html
    }
