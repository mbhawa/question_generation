from django.urls import path

from . import views

app_name = "data_loader"

urlpatterns = [
    path(
        "url/",
        views.input_url_view,
        name="input_url_view",
    ),
    path(
        "pdf/",
        views.input_pdf_view,
        name="input_pdf_view",
    ),
    path(
        "text/",
        views.input_text_view,
        name="input_text_view",
    ),
    path(
        "media/",
        views.input_media_view,
        name="input_media_view",
    ),
    path(
        "doc/",
        views.input_doc_view,
        name="input_doc_view",
    ),
]
