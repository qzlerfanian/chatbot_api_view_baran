from django.db import models

class Upload(models.Model):
    file = models.FileField(upload_to='uploads/')
    extracted_text = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Upload {self.id}"
