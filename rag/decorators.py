from django.shortcuts import redirect
from django.contrib import messages
# rag/decorators.py
from chatgpt_app.models import UserProfile

def approved_user_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        try:
            if not request.user.userprofile.is_approved:
                messages.error(request, "حساب شما هنوز تأیید نشده است.")
                return redirect('not_approved')
        except:
            messages.error(request, "پروفایل شما موجود نیست.")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper
