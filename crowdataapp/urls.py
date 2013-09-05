from django.conf.urls import patterns, url
from crowdataapp import views

urlpatterns = patterns('',
                       url(r'(?P<document_set>[\w-]+)', views.document_set_landing, name='document_set_landing'),
                       url(r'(?P<document_set>[\w-]+)/(?P<document_id>\d+)/transcriptions/new',
                           views.transcription_new,
                           name='new_transcription'),
                       url(r'(?P<document_set>[\w-]+)/another',
                           views.redirect_to_new_transcription,
                           name='get_new_transcription'),
                       url(r'crowdata/form/(?P<slug>[\w-]+)',
                           views.form_detail,
                           name='crowdata_form_detail')
)
