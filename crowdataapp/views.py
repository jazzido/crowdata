import re

from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404

from annoying.decorators import render_to

from crowdataapp import models


@render_to('transcription_new.html')
def transcription_new(request, document_id):
    document = get_object_or_404(models.Document, pk=document_id)

    document_embed_url = re.match(r'^(.+)\.html$', document.url).group(1) + '.js'

    print document.document_set.form

    return {
        'document': document,
        'document_embed_url': document_embed_url
    }
