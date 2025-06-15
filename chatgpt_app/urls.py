from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('chat/', views.chat_view, name='chat'),
    path('send/', views.send_message, name='send_message'),
    path('new_session/', views.new_session, name='new_session'),
    path('delete/<int:session_id>/', views.delete_session, name='delete_session'),
    path('rename/<int:session_id>/', views.rename_session, name='rename_session'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('profile/', views.profile, name='user_dashboard'),
    path('dashboard/', views.dashboard_view, name='dashboard'),

]

