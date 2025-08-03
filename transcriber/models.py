# from django.db import models
#
# class AudioFile(models.Model):
#     audio = models.FileField(upload_to='audio/')
#     transcript = models.TextField(blank=True, null=True)
#     uploaded_at = models.DateTimeField(auto_now_add=True)

from django.db import models

class AudioFile(models.Model):
    audio = models.FileField(upload_to='audio/')
    transcript = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"فایل صوتی {self.id}"
