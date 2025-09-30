from rest_framework import serializers
from .models import FileChat, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id','role','content','created_at']


class FileChatSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    class Meta:
        model = FileChat
        fields = ['id','name','vector_store_id','created_at','messages']