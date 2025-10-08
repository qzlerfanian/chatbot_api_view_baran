from django.db import models
from django.contrib.auth.models import User

class FileChat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="file_chats")
    name = models.CharField(max_length=255)
    vector_store_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class Message(models.Model):
    file_chat = models.ForeignKey(FileChat, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=(('user','user'),('assistant','assistant')))
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)