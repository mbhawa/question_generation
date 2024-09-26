from django.db import models

class CustomFileField(models.FileField):
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 255  # Increase the max_length as required
        super().__init__(*args, **kwargs)
