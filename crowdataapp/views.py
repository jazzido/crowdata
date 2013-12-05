# coding: utf-8
from django.shortcuts import get_object_or_404, redirect, render_to_response

from django.utils.translation import ugettext, ugettext_lazy as _
from django.core.urlresolvers import resolve, reverse
from django.db.models import Count
from django.db.models.signals import post_save
from django.template import RequestContext
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages


from annoying.decorators import render_to
from forms_builder.forms.signals import form_valid, form_invalid

from crowdataapp import models, forms

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

def form_detail(request, slug, template="forms/form_detail.html"):
    form = get_object_or_404(models.DocumentSetForm, slug=slug)
    request_context = RequestContext(request)
    args = (form, request_context, request.POST or None)

    form_for_form = forms.DocumentSetFormForForm(*args)

    if request.method == 'POST':
        if not form_for_form.is_valid():
            form_invalid.send(sender=request, form=form_for_form)
        else:
            entry = form_for_form.save()
            form_valid.send(sender=request, form=form_for_form, entry=entry, document_id=request.session['document_id_for_entry'])
            return HttpResponse('')
    return render_to_response(template, { 'form': form }, request_context)


@login_required
def transcription_new(request, document_set):
    doc_set = get_object_or_404(models.DocumentSet, slug=document_set)

    candidates = doc_set.get_pending_documents() \
                        .exclude(form_entries__user=request.user)

    if candidates.count() == 0:
        # TODO Redirect to a message page: "you've gone through all the documents in this project!"
        return render_to_response('no_more_documents.html',
                                  { 'document_set': doc_set },
                                  context_instance=RequestContext(request))

    document = candidates.order_by('?')[0]

    # save the candidate document in the session, for later use
    # in signals.create_entry
    request.session['document_id_for_entry'] = document.id

    return render_to_response('transcription_new.html',
                              {
                                  'document': document,
                                  'head_html': document.document_set.head_html
                              },
                              context_instance=RequestContext(request))

@render_to('login_page.html')
def login(request):
    if 'next' in request.GET:
        request.session['redirect_after_login'] = request.GET['next']

    return {}

def after_login(request):
    # TODO: if user hasn't completed his profile, ask him/her to do so.
    # (we need his/her name, ask if he wants to appear in the leaderboards, etc)
    if not models.UserProfile.objects.filter(user=request.user).exists():
        # TODO set message 'you need to set your profile'
        messages.warning(request, _('You need to complete your profile'))
        return redirect(reverse('edit_profile'))
    elif 'redirect_after_login' in request.session:
        redir = request.session['redirect_after_login']
        del request.session['redirect_after_login']
        return redirect(redir)
    else:
        return redirect(reverse('document_set_index'))

@render_to('edit_profile.html')
def edit_profile(request):
    """ Profile Edit """
    try:
        profile = instance=models.UserProfile.objects.get(user=request.user)
    except models.UserProfile.DoesNotExist:
        profile = None

    if request.method == 'POST':
        form = forms.UserProfileForm(data=request.POST, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            if 'redirect_after_login' in request.session:
                redir = request.session['redirect_after_login']
                del request.session['redirect_after_login']
                return redirect(redir)
            else:
                return redirect(reverse('edit_profile'))
    else:
        form = forms.UserProfileForm(instance=profile)

    return {
        'profile_form': form
    }
