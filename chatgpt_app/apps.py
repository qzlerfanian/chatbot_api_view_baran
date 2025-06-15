# chatgpt_app/apps.py

from django.apps import AppConfig


class ChatgptAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chatgpt_app'

    def ready(self):
        import chatgpt_app.signals
