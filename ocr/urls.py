from django.contrib import admin
from django.urls import path
from ocr import views

urlpatterns = [
    path('', views.upload_view, name='ocr'),
    path('result/<int:pk>/', views.result_view, name='result'),
    path('download/docx/<int:pk>/', views.download_docx, name='download_docx'),
    path('download/pdf/<int:pk>/', views.download_pdf, name='download_pdf'),
]
