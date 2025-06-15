from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
import openai , os, time , base64
from django.db.models import Sum
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .models import ChatSession, Message, TokenUsage, UserProfile
from .utils import call_openrouter
from django.utils.timezone import now , timedelta
from .forms import UploadForm
from PIL import Image
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import base64
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth


MAX_TOKENS = 5000
MIN_INTERVAL_SECONDS = 2
USER_LAST_MESSAGE_TIME = {}


def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = User.objects.create_user(username=username, password=password)
        login(request, user)
        return redirect('user_dashboard')
    return render(request, 'register.html')

def login_view(request):
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST['username'],
            password=request.POST['password']
        )
        if user:
            login(request, user)
            return redirect('user_dashboard')
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def profile(request):
    return render(request, 'profile.html')


@login_required
def chat_view(request):
    session_id = request.GET.get('session_id')
    sessions = ChatSession.objects.filter(user=request.user).order_by('-updated_at')

    if session_id:
        active_session = ChatSession.objects.get(id=session_id, user=request.user)
        messages = Message.objects.filter(session=active_session).order_by('timestamp')
    elif sessions.exists():
        active_session = sessions.first()
        messages = Message.objects.filter(session=active_session).order_by('timestamp')
    else:
        active_session = None
        messages = []

    # 🔢 مجموع توکن‌های داده‌شده
    given_tokens = TokenUsage.objects.filter(user=request.user).aggregate(Sum('tokens'))['tokens__sum'] or 0

    # 🔻 مجموع توکن‌های استفاده‌شده در پیام‌ها
    used_tokens = Message.objects.filter(user=request.user).aggregate(Sum('total_tokens'))['total_tokens__sum'] or 0

    # ✳️ توکن باقی‌مانده
    remaining_tokens = given_tokens - used_tokens

    return render(request, 'chat.html', {
        'messages': messages,
        'sessions': sessions,
        'active_session': active_session,
        'given_tokens': given_tokens,
        'used_tokens': used_tokens,
        'remaining_tokens': remaining_tokens,
    })

@login_required
def new_session(request):
    session = ChatSession.objects.create(
        user=request.user,
        title="چت جدید",
        updated_at=datetime.now()
    )
    return redirect(f'/chat/?session_id={session.id}')

@login_required
def delete_session(request, session_id):
    ChatSession.objects.filter(id=session_id, user=request.user).delete()
    return redirect('/chat/')

from django.http import JsonResponse

@login_required
def rename_session(request, session_id):
    if request.method == 'POST':
        new_title = request.POST.get('title', '').strip()
        session = ChatSession.objects.get(id=session_id, user=request.user)
        session.title = new_title[:100]
        session.save()
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'invalid'}, status=400)

@staff_member_required  # فقط ادمین‌ها دسترسی دارن
def admin_panel(request):
    users = User.objects.all()
    data = []

    for user in users:
        total = TokenUsage.objects.filter(user=user).aggregate(Sum('tokens'))['tokens__sum'] or 0
        data.append({'username': user.username, 'email': user.email, 'tokens': total})

    return render(request, 'admin_panel.html', {'data': data})

# استفاده از  gpt  واقعی
client = openai.OpenAI(api_key= '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'
)  # ← کلید API اینجا قرار می‌گیره یا از env

USER_LAST_MESSAGE_TIME = {}
MIN_INTERVAL_SECONDS = 5

@login_required
def send_message(request):
    if request.method == 'POST':
        current_time = datetime.now()
        user = request.user
        profiles = user.userprofile

        if not profiles.is_approved:
            return HttpResponse("⛔ حساب شما هنوز تأیید نشده است.", status=403)

        user_id = user.id
        last_time = USER_LAST_MESSAGE_TIME.get(user_id)
        if last_time and (current_time - last_time).total_seconds() < MIN_INTERVAL_SECONDS:
            return HttpResponse("⏳ لطفاً چند ثانیه صبر کنید.", status=429)
        USER_LAST_MESSAGE_TIME[user_id] = current_time

        form = UploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return HttpResponse("❌ ارسال نامعتبر بود.", status=400)

        prompt = form.cleaned_data.get('prompt', '')
        session_id = request.POST.get('session_id')

        chat_session = get_object_or_404(ChatSession, id=session_id, user=user) if session_id else ChatSession.objects.create(user=user, title=prompt[:30] or "جلسه جدید")
        chat_session.updated_at = now()
        chat_session.save()

        try:
            image = form.cleaned_data.get("image")
            audio = form.cleaned_data.get("audio")
            document = form.cleaned_data.get("document")

            if image:
                # ذخیره‌سازی و ایجاد URL عمومی
                path = default_storage.save(f'uploads/{image.name}', ContentFile(image.read()))
                image_url = request.build_absolute_uri(default_storage.url(path))

                # GPT-4o مدل جدید ویژن
                result = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt or "این تصویر را تحلیل کن"},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }],
                    max_tokens=1000
                )
                reply = result.choices[0].message.content
                usage = result.usage

            elif audio:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio
                )
                result = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": transcript.text}]
                )
                reply = result.choices[0].message.content
                usage = result.usage

            elif document:
                # API beta فایل‌ها، در صورت فعال بودن
                file_response = client.files.create(file=document, purpose="assistants")
                reply = "✅ فایل شما آپلود شد ولی فعلاً پشتیبانی از تحلیل مستقیم فایل فعال نیست."
                usage = {'total_tokens': 0, 'prompt_tokens': 0, 'completion_tokens': 0}

            else:
                result = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}]
                )
                reply = result.choices[0].message.content
                usage = result.usage

        except Exception as e:
            return HttpResponse(f"🚫 خطا در تحلیل: {str(e)}", status=500)

        # پردازش توکن
        total_tokens = usage.total_tokens if hasattr(usage, 'total_tokens') else usage.get('total_tokens', 0)
        prompt_tokens = getattr(usage, 'prompt_tokens', 0)
        completion_tokens = getattr(usage, 'completion_tokens', 0)

        if profiles.token_balance < total_tokens:
            return HttpResponse("🛑 توکن‌های شما کافی نیست.", status=403)

        Message.objects.create(
            user=user,
            session=chat_session,
            prompt=prompt or "[فایل ارسال شد]",
            response=reply,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

        profiles.token_balance -= total_tokens
        profiles.save()

        TokenUsage.objects.create(user=user, tokens=-total_tokens)

        return redirect(f'/chat/?session_id={chat_session.id}')



@login_required
def dashboard_view(request):
    user = request.user
    today = now().date()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)

    # مجموع توکن‌ها
    given_tokens = TokenUsage.objects.filter(user=user, tokens__gt=0).aggregate(Sum('tokens'))['tokens__sum'] or 0
    used_tokens = TokenUsage.objects.filter(user=user, tokens__lt=0).aggregate(Sum('tokens'))['tokens__sum'] or 0
    remaining_tokens = given_tokens + used_tokens  # چون used منفی ذخیره شده

    # آمار دوره‌ای
    daily_used = abs(TokenUsage.objects.filter(user=user, tokens__lt=0, created_at__date=today).aggregate(Sum('tokens'))['tokens__sum'] or 0)
    weekly_used = abs(TokenUsage.objects.filter(user=user, tokens__lt=0, created_at__date__gte=start_of_week).aggregate(Sum('tokens'))['tokens__sum'] or 0)
    monthly_used = abs(TokenUsage.objects.filter(user=user, tokens__lt=0, created_at__date__gte=start_of_month).aggregate(Sum('tokens'))['tokens__sum'] or 0)

    # آماده‌سازی داده برای نمودار (7 روز گذشته)
    last_7_days = now() - timedelta(days=6)
    usage_per_day = (
        TokenUsage.objects
        .filter(user=user, tokens__lt=0, created_at__gte=last_7_days)
        .annotate(day=TruncDay('created_at'))
        .values('day')
        .annotate(total=Sum('tokens'))
        .order_by('day')
    )

    chart_data = [{'day': item['day'].strftime('%Y-%m-%d'), 'tokens': abs(item['total'])} for item in usage_per_day]

    return render(request, 'dashboard.html', {
        'given_tokens': given_tokens,
        'used_tokens': abs(used_tokens),
        'remaining_tokens': remaining_tokens,
        'daily_used': daily_used,
        'weekly_used': weekly_used,
        'monthly_used': monthly_used,
        'chart_data': chart_data
    })