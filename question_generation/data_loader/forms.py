from conf.constant import constant_config
from django import forms

from .models import UploadedFile


class URLForm(forms.Form):
    user_id = forms.CharField(label="User ID")
    url = forms.CharField(label="URL")


class PDFUploadFileForm(forms.ModelForm):
    user_id = forms.CharField(label="User ID")

    class Meta:
        model = UploadedFile
        fields = ["file"]


class TextForm(forms.Form):
    user_id = forms.CharField(label="User ID")
    text = forms.CharField(
        label="Text",
        widget=forms.Textarea,
        # max_length=constant_config.get("max_text_length"),
    )


class MediaUploadFileForm(forms.ModelForm):
    user_id = forms.CharField(label="User ID")

    class Meta:
        model = UploadedFile
        fields = ["file"]


class DocUploadFileForm(forms.ModelForm):
    user_id = forms.CharField(label="User ID")

    class Meta:
        model = UploadedFile
        fields = ["file"]
