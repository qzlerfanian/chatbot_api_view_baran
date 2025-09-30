from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("chat/<int:chat_id>/", views.chat_view, name="chat"),
    path("delete/<int:chat_id>/", views.delete_chat, name="delete_chat"),
]
