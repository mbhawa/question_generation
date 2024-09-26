# from django.db import models
# from .fields import CustomFileField  # Import the custom file field


# class UploadedFile(models.Model):
#     file = models.FileField(upload_to="uploads/")




from django.db import models
from .fields import CustomFileField  # Import the custom file field

class UploadedFile(models.Model):
    file = CustomFileField(upload_to="uploads/")
