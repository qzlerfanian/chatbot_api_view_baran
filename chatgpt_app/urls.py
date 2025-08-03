from django.urls import path
from . import views
from django.contrib.auth import views as auth_views  # ✅ اصلاح این خط

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('chat/', views.chat_view, name='chat'),
    path('send/', views.send_message, name='send_message'),
    path('new_session/', views.new_session, name='new_session'),
    path('delete/<int:session_id>/', views.delete_session, name='delete_session'),
    path('rename/<int:session_id>/', views.rename_session, name='rename_session'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('profile/', views.profile, name='user_dashboard'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('change-password/', views.change_password_view, name='change_password'),

    # 🔐 مسیرهای ریست پسورد با استفاده از auth_view
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),
]
