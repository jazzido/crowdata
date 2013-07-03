from django.conf.urls import patterns, url
from crowdataapp import views

urlpatterns = patterns('',
                       url(r'(?P<document_set>[\w-]+)/(?P<document_id>\d+)/transcriptions/new',
                           views.transcription_new,
                           name='new_transcription'),
                       url(r'(?P<document_set>[\w-]+)/another',
                           views.redirect_to_new_transcription,
                           name='get_new_transcription')
)
