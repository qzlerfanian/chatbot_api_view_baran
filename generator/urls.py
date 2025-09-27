from django.urls import path
from .views import generate_image , index

urlpatterns = [
    path('', generate_image, name='generate_image'),
    path('image/', index, name="index"),
]
