from django.urls import path
from . import views

urlpatterns = [
    path('uploadfile/', views.upload_file, name='upload_file'),
    #path('ask/', views.chat_with_session, name='ask_question'),
    path('not-approved/', views.not_approved, name='not_approved'),
    path('file/<int:file_id>/new_session/', views.create_chat_session, name='create_chat_session'),
    path('session/<int:session_id>/chat/', views.chat_with_session, name='chat_with_session'),

]
