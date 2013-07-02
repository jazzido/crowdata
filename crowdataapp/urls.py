from django.conf.urls import patterns, url
from crowdataapp import views

urlpatterns = patterns('',
                       url(r'document/(?P<document_id>\d+)/transcriptions/new',
                           views.transcription_new,
                           name='new_transcription')
)
