import io
import traceback
from http import HTTPStatus
from pathlib import Path

from conf.constant import constant_config
from data_loader.utils.topic_extractor import TopicExtractor
from data_loader.utils.utils import (
    generate_sha_key,
    get_loader,
    is_url,
    process_document,
    process_media,
    process_pdf,
    process_text,
    process_url,
)
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .forms import (
    DocUploadFileForm,
    MediaUploadFileForm,
    PDFUploadFileForm,
    TextForm,
    URLForm,
)


@csrf_exempt
def input_url_view(request):
    data = {"url": ""}
    if request.method == "POST":
        form = URLForm(request.POST)
        if form.is_valid():
            # Process the valid form data, e.g., save to database
            url = form.cleaned_data["url"]
            user_id = form.cleaned_data["user_id"]
            if not is_url(url):
                return JsonResponse({"Error": "Entered URL is not valid"})
            try:
                return process_url(url=url, user_id=user_id)
            except Exception:
                return JsonResponse(
                    {"Error": f"An error occured: {traceback.format_exc()}"}
                )
    else:
        form = URLForm()
    return render(request, "url.html", {"form": form})


@csrf_exempt
def input_pdf_view(request):
    # data = {}
    if request.method == "POST":
        form = PDFUploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            user_id = form.cleaned_data["user_id"]
            uploaded_file = form.save(commit=False)
            try:
                return process_pdf(uploaded_file=uploaded_file, user_id=user_id)
            except Exception as e:
                return JsonResponse(
                    {"Error": f"An error occured: {traceback.format_exc()}"}
                )

    else:
        form = PDFUploadFileForm()
    return render(request, "pdf.html", {"form": form})


@csrf_exempt
def input_text_view(request):
    if request.method == "POST":
        form = TextForm(request.POST)
        if form.is_valid():
            # Process the valid form data, e.g., save to database
            text = form.cleaned_data["text"]
            user_id = form.cleaned_data["user_id"]
            if is_url(text):
                return JsonResponse(
                    {
                        "Error": "Received URL instead of text. If you want to parse a URL, please use the URL parser functionality"
                    }
                )
            # put this in task.py and import it from there
            if len(text) > constant_config.get("max_text_length"):
                raise Exception(
                    f"Maximum allowed text length is {constant_config.get('max_text_length')}, while you provided text of length {len(text)}"
                )
            try:
                return process_text(text=text, user_id=user_id)
            except Exception as e:
                return JsonResponse(
                    {"Error": f"An error occured: {traceback.format_exc()}"}
                )
    else:
        form = TextForm()
    return render(request, "text.html", {"form": form})


@csrf_exempt
def input_media_view(request):
    if request.method == "POST":
        form = MediaUploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            user_id = form.cleaned_data["user_id"]
            uploaded_file = form.save(commit=False)
            try:
                return process_media(uploaded_file=uploaded_file, user_id=user_id)
            except Exception:
                return JsonResponse(
                    {"Error": f"An error occured: {traceback.format_exc()}"}
                )
    else:
        form = MediaUploadFileForm()

    return render(request, "media.html", {"form": form})


@csrf_exempt
def input_doc_view(request):
    if request.method == "POST":
        form = DocUploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            user_id = form.cleaned_data["user_id"]
            uploaded_file = form.save(commit=False)
            try:
                return process_document(uploaded_file=uploaded_file, user_id=user_id)
            except Exception:
                return JsonResponse(
                    {"Error": f"An error occured: {traceback.format_exc()}"}
                )
    else:
        form = DocUploadFileForm()

    return render(request, "doc.html", {"form": form})
