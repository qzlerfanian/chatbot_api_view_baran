from django.db import models


class FileChat(models.Model):
    name = models.CharField(max_length=255)
    vector_store_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Message(models.Model):
    file_chat = models.ForeignKey(FileChat, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=(('user','user'),('assistant','assistant')))
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)