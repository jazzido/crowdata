from django.conf.urls import patterns, url
from crowdataapp import views

urlpatterns = patterns('crowdataapp.views',
                       url(r'^$',
                           'document_set_index',
                           name='document_set_index'),
                       url(r'^pleaselogin$',
                           'login',
                           name='login_page'),
                       url(r'^afterlogin$',
                           'after_login',
                           name='after_login'),
                       url(r'^(?P<document_set>[\w-]+)$',
                           'document_set_view',
                           name='document_set_view'),
                       url(r'^(?P<document_set>[\w-]+)/another$',
                           'redirect_to_new_transcription',
                           name='get_new_transcription'),
                       url(r'^(?P<document_set>[\w-]+)/(?P<document_id>\d+)/transcriptions/new$',
                           'transcription_new',
                           name='new_transcription'),
                       url(r'crowdata/form/(?P<slug>[\w-]+)',
                           'form_detail',
                           name='crowdata_form_detail'),

)
