from django.urls import path
from . import views

urlpatterns = [
    path("index/", views.index, name="index"),
    path("upload_image/", views.upload_image, name="upload_image"),
    path("ask/", views.ask, name="ask"),
]
