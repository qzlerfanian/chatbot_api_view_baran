from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
import openai , os, time , base64
from django.db.models import Sum
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import  get_object_or_404
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
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.forms import PasswordChangeForm



MAX_TOKENS = 5000
MIN_INTERVAL_SECONDS = 2
USER_LAST_MESSAGE_TIME = {}


def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']

        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': 'The username is already taken.'})

        if User.objects.filter(email=email).exists():
            return render(request, 'register.html', {'error': 'The email is already in use.'})

        user = User.objects.create_user(username=username, email=email, password=password)
        login(request, user)
        return redirect('user_dashboard')

    return render(request, 'register.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect('user_dashboard')
        else:
            messages.error(request, 'The username or password is incorrect.')

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # مانع از خروج کاربر بعد از تغییر رمز
            messages.success(request, 'The password has been changed successfully.')
            return redirect('user_dashboard')
        else:
            messages.error(request, 'please check the form')
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'change_password.html', {'form': form})

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
        title="چت جدید",  # یا "جلسه جدید" اگر دوست داری پیش‌فرض باشه
        updated_at=now()
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


def generate_chat_title(prompt, image, audio, document):
    print("🔤 GENERATING TITLE from:", prompt, image, audio, document)  # برای بررسی
    if prompt:
        return prompt.strip().split('\n')[0][:30]
    elif image:
        return "تحلیل تصویر 📷"
    elif audio:
        return "تحلیل صدا 🎧"
    elif document:
        return "بررسی سند 📄"
    else:
        return "جلسه جدید"


#
# @login_required
# def send_message(request):
#     if request.method == 'POST':
#         current_time = datetime.now()
#         user = request.user
#         profiles = user.userprofile
#
#         if not profiles.is_approved:
#             return HttpResponse("⛔ your account not accepted , please waiting for Admin", status=403)
#
#         user_id = user.id
#         last_time = USER_LAST_MESSAGE_TIME.get(user_id)
#         if last_time and (current_time - last_time).total_seconds() < MIN_INTERVAL_SECONDS:
#             return HttpResponse("⏳ please wait a moment!", status=429)
#         USER_LAST_MESSAGE_TIME[user_id] = current_time
#
#         form = UploadForm(request.POST, request.FILES)
#         if not form.is_valid():
#             return HttpResponse("❌ ارسال نامعتبر بود.", status=400)
#
#         prompt = form.cleaned_data.get('prompt', '')
#         image = form.cleaned_data.get("image")
#         audio = form.cleaned_data.get("audio")
#         document = form.cleaned_data.get("document")
#         session_id = request.POST.get('session_id')
#
#         print("🟢 PROMPT:", prompt)
#         print("📎 FILES:", image, audio, document)
#
#         if session_id:
#             chat_session = get_object_or_404(ChatSession, id=session_id, user=user)
#
#             # 🔥 اگر عنوان هنوز "چت جدید" بود، برو سراغ تولید عنوان جدید
#             if chat_session.title.strip() == "چت جدید":
#                 new_title = generate_chat_title(prompt, image, audio, document)
#                 print("🎯 NEW TITLE GENERATED:", new_title)
#                 if new_title and new_title != "چت جدید":
#                     chat_session.title = new_title
#
#         else:
#             new_title = generate_chat_title(prompt, image, audio, document)
#             chat_session = ChatSession.objects.create(
#                 user=user,
#                 title=new_title,
#                 updated_at=now()
#             )
#
#         chat_session.updated_at = now()
#         chat_session.save()
#
#         try:
#             if image:
#                 path = default_storage.save(f'uploads/{image.name}', ContentFile(image.read()))
#                 image_url = request.build_absolute_uri(default_storage.url(path))
#
#                 result = client.chat.completions.create(
#                     model="gpt-4o",
#                     messages=[{
#                         "role": "user",
#                         "content": [
#                             {"type": "text", "text": prompt or "این تصویر را تحلیل کن"},
#                             {"type": "image_url", "image_url": {"url": image_url}}
#                         ]
#                     }],
#                     max_tokens=1000
#                 )
#                 reply = result.choices[0].message.content
#                 usage = result.usage
#
#             elif audio:
#                 transcript = client.audio.transcriptions.create(
#                     model="whisper-1",
#                     file=audio
#                 )
#                 result = client.chat.completions.create(
#                     model="gpt-3.5-turbo",
#                     messages=[{"role": "user", "content": transcript.text}]
#                 )
#                 reply = result.choices[0].message.content
#                 usage = result.usage
#
#             elif document:
#                 file_response = client.files.create(file=document, purpose="assistants")
#                 reply = "✅ فایل شما آپلود شد ولی فعلاً پشتیبانی از تحلیل مستقیم فایل فعال نیست."
#                 usage = {'total_tokens': 0, 'prompt_tokens': 0, 'completion_tokens': 0}
#
#             else:
#                 system_message = {
#                     "role": "system",
#                     "content": (
#                         "شما یک دستیار حرفه‌ای و مودب هستید که به زبان فارسی پاسخ می‌دهید. پاسخ‌ها باید:\n"
#                         "- ساختاریافته باشند ✅\n"
#                         "- شامل تیترهای برجسته (Bold) برای بخش‌های مختلف باشند 📝\n"
#                         "- در صورت نیاز لیست‌وار توضیح داده شوند 🔹\n"
#                         "- از علائم نگارشی درست استفاده شود ✍️\n"
#                         "- از ایموجی برای زیباتر شدن پاسخ بهره بگیرید 😊\n"
#                         "- پاسخ شامل مقدمه، بدنه و جمع‌بندی باشد 📚\n\n"
#                         "پاسخ‌ها باید شبیه خروجی چت‌بات ChatGPT باشند؛ مفصل، خوانا، و با لحن دوستانه و حرفه‌ای.\n"
#                         "انگلیسی ها رو چپ چین کن .\n"
#                         "اگر کاربر سؤال کوتاهی پرسید، شما باز هم پاسخ کامل و توضیح‌دار بدهید."
#
#                         "```python\nprint(\"سلام دنیا\")\n```\n\n"
#                         " بین بخش‌ها فاصله بگذار، و در صورت نیاز تیترها را bold کن با **. متن باید بسیار مرتب و خوانا باشد."
#                     )
#                 }
#
#                 previous_messages = Message.objects.filter(session=chat_session).order_by('-id')[:10]
#                 history = [system_message]
#                 for m in reversed(previous_messages):
#                     history.append({"role": "user", "content": m.prompt})
#                     history.append({"role": "assistant", "content": m.response})
#
#                 history.append({"role": "user", "content": prompt})
#
#                 result = client.chat.completions.create(
#                     model="gpt-4o",
#                     messages=history,
#                     max_tokens=1200,
#                     temperature=0.7
#                 )
#                 reply = result.choices[0].message.content
#                 usage = result.usage
#
#
#         except Exception as e:
#             return HttpResponse(f"🚫 خطا در تحلیل: {str(e)}", status=500)
#
#         total_tokens = usage.total_tokens if hasattr(usage, 'total_tokens') else usage.get('total_tokens', 0)
#         prompt_tokens = getattr(usage, 'prompt_tokens', 0)
#         completion_tokens = getattr(usage, 'completion_tokens', 0)
#
#         if profiles.token_balance < total_tokens:
#             return HttpResponse("🛑 your token is not enough ! ", status=403)
#
#         Message.objects.create(
#             user=user,
#             session=chat_session,
#             prompt=prompt or "[فایل ارسال شد]",
#             response=reply,
#             prompt_tokens=prompt_tokens,
#             completion_tokens=completion_tokens,
#             total_tokens=total_tokens,
#         )
#
#         profiles.token_balance -= total_tokens
#         profiles.save()
#
#         TokenUsage.objects.create(user=user, tokens=-total_tokens)
#
#         return redirect(f'/chat/?session_id={chat_session.id}')


from duckduckgo_search import DDGS

def search_web_snippet(query: str) -> str:
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query)
            return results[0]['body'] if results else ""
    except Exception as e:
        print("🔴 Web search failed:", e)
        return ""




@login_required
def send_message(request):
    if request.method == 'POST':
        current_time = datetime.now()
        user = request.user
        profiles = user.userprofile

        if not profiles.is_approved:
            return HttpResponse("⛔ your account not accepted , please waiting for Admin", status=403)

        user_id = user.id
        last_time = USER_LAST_MESSAGE_TIME.get(user_id)
        if last_time and (current_time - last_time).total_seconds() < MIN_INTERVAL_SECONDS:
            return HttpResponse("⏳ please wait a moment!", status=429)
        USER_LAST_MESSAGE_TIME[user_id] = current_time

        form = UploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return HttpResponse("❌ ارسال نامعتبر بود.", status=400)

        prompt = form.cleaned_data.get('prompt', '')
        image = form.cleaned_data.get("image")
        audio = form.cleaned_data.get("audio")
        document = form.cleaned_data.get("document")
        session_id = request.POST.get('session_id')

        print("🟢 PROMPT:", prompt)
        print("📎 FILES:", image, audio, document)

        if session_id:
            chat_session = get_object_or_404(ChatSession, id=session_id, user=user)

            # 🔥 اگر عنوان هنوز "چت جدید" بود، برو سراغ تولید عنوان جدید
            if chat_session.title.strip() == "چت جدید":
                new_title = generate_chat_title(prompt, image, audio, document)
                print("🎯 NEW TITLE GENERATED:", new_title)
                if new_title and new_title != "چت جدید":
                    chat_session.title = new_title

        else:
            new_title = generate_chat_title(prompt, image, audio, document)
            chat_session = ChatSession.objects.create(
                user=user,
                title=new_title,
                updated_at=now()
            )

        chat_session.updated_at = now()
        chat_session.save()

        try:
            if image:
                path = default_storage.save(f'uploads/{image.name}', ContentFile(image.read()))
                image_url = request.build_absolute_uri(default_storage.url(path))

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
                file_response = client.files.create(file=document, purpose="assistants")
                reply = "✅ فایل شما آپلود شد ولی فعلاً پشتیبانی از تحلیل مستقیم فایل فعال نیست."
                usage = {'total_tokens': 0, 'prompt_tokens': 0, 'completion_tokens': 0}

            else:
                system_message = {
                    "role": "system",
                    "content": (
                        "شما یک دستیار حرفه‌ای و مودب هستید که به زبان فارسی پاسخ می‌دهید. پاسخ‌ها باید:\n"
                        "- ساختاریافته باشند ✅\n"
                        "- شامل تیترهای برجسته (Bold) برای بخش‌های مختلف باشند 📝\n"
                        "- در صورت نیاز لیست‌وار توضیح داده شوند 🔹\n"
                        "- از علائم نگارشی درست استفاده شود ✍️\n"
                        "- از ایموجی برای زیباتر شدن پاسخ بهره بگیرید 😊\n"
                        "- پاسخ شامل مقدمه، بدنه و جمع‌بندی باشد 📚\n\n"
                        "پاسخ‌ها باید شبیه خروجی چت‌بات ChatGPT باشند؛ مفصل، خوانا، و با لحن دوستانه و حرفه‌ای.\n"
                        "انگلیسی ها رو چپ چین کن .\n"
                        "اگر کاربر سؤال کوتاهی پرسید، شما باز هم پاسخ کامل و توضیح‌دار بدهید."

                        "```python\nprint(\"سلام دنیا\")\n```\n\n"
                        " بین بخش‌ها فاصله بگذار، و در صورت نیاز تیترها را bold کن با **. متن باید بسیار مرتب و خوانا باشد."
                    )
                }

                previous_messages = Message.objects.filter(session=chat_session).order_by('-id')[:10]
                history = [system_message]
                for m in reversed(previous_messages):
                    history.append({"role": "user", "content": m.prompt})
                    history.append({"role": "assistant", "content": m.response})

                # 🔍 اگر به نظر رسید نیاز به سرچ وب هست، انجام بده
                search_keywords = ["دلار","ملک","اخبار", "هوا", "قیمت", "کی", "چند", "کجا", "چگونه", "آخرین"]
                if any(word in prompt for word in search_keywords):
                    web_info = search_web_snippet(prompt)
                    if web_info:
                        prompt += f"\n\n🛰 این اطلاعات از جستجوی وب پیدا شد:\n{web_info}"

                history.append({"role": "user", "content": prompt})

                result = client.chat.completions.create(
                    model="gpt-4o",
                    messages=history,
                    max_tokens=1200,
                    temperature=0.7
                )
                reply = result.choices[0].message.content
                usage = result.usage


        except Exception as e:
            return HttpResponse(f"🚫 خطا در تحلیل: {str(e)}", status=500)

        total_tokens = usage.total_tokens if hasattr(usage, 'total_tokens') else usage.get('total_tokens', 0)
        prompt_tokens = getattr(usage, 'prompt_tokens', 0)
        completion_tokens = getattr(usage, 'completion_tokens', 0)

        if profiles.token_balance < total_tokens:
            return HttpResponse("🛑 your token is not enough ! ", status=403)

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