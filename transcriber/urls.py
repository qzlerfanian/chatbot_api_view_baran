from django.urls import path
from .views import upload_audio , download_word

urlpatterns = [
    path('upload/', upload_audio, name='upload_audio'),
    path('download/<int:audio_id>/', download_word, name='download_word'),
]
