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
import base64
import mimetypes
from io import BytesIO
from django.core.files.base import ContentFile
# اگر می‌خوای تصاویر را قبل از ارسال فشرده کنی (اختیاری)
try:
    from PIL import Image
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False



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
# client = openai.OpenAI(api_key= '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'
# )


# ← کلید API اینجا قرار می‌گیره یا از env
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

if OpenAI:
    client = OpenAI(api_key= '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'
    )
else:
    client = None


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


try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

def search_web_snippet(query: str) -> str:
    if not DDGS:
        return "Search functionality not available"
    
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
        document = request.FILES.get("document")
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
            # -------------------------
            # جایگزین این بخش در ویو send_message
            # -------------------------
            if image:
                try:
                    # 1) بخوان تصویر به‌صورت بایت (یک‌بار بخوان؛ اگر می‌خواهی هم ذخیره کنی از همین bytes استفاده کن)
                    image_bytes = image.read()

                    # 2) (اختیاری) فشرده‌سازی با PIL برای جلوگیری از ارسال تصویر خیلی بزرگ
                    if PIL_AVAILABLE:
                        try:
                            pil_img = Image.open(BytesIO(image_bytes))
                            # محدودکننده اندازه (مثال: طول یا عرض حداکثر 1024)
                            pil_img.thumbnail((1024, 1024))
                            out = BytesIO()
                            # اگر تصویر شفافیت داشت، آن را به RGB تبدیل کن تا JPEG قابل ذخیره باشد
                            if pil_img.mode in ("RGBA", "LA"):
                                background = Image.new("RGB", pil_img.size, (255, 255, 255))
                                background.paste(pil_img, mask=pil_img.split()[3])
                                background.save(out, format="JPEG", quality=75)
                            else:
                                pil_img.save(out, format="JPEG", quality=75)
                            image_bytes = out.getvalue()
                            image_mime = "image/jpeg"
                        except Exception:
                            # در صورت خطا در پردازش PIL، به حالت پیش‌فرض ادامه بده
                            image_mime = getattr(image, "content_type", None) or mimetypes.guess_type(image.name)[
                                0] or "image/jpeg"
                    else:
                        image_mime = getattr(image, "content_type", None) or mimetypes.guess_type(image.name)[
                            0] or "image/jpeg"

                    # 3) (اختیاری) اگر می‌خواهی همچنان فایل را در storage ذخیره کنی:
                    # توجه: اگر تصویر را ذخیره کردی دیگر نیازی به ری‌خواندن فایلت نیست چون bytes را نگه داشتیم.
                    try:
                        default_storage.save(f'uploads/{image.name}', ContentFile(image_bytes))
                    except Exception:
                        # اگر ذخیره به هر دلیل ناموفق بود، ادامه می‌دهیم چون برای ارسال به مدل نیازی به URL نداریم
                        pass

                    # 4) ساخت data URI
                    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                    data_uri = f"data:{image_mime};base64,{image_base64}"

                    # 5) ارسال به API با همان الگوی شما (data URI به‌جای URL عمومی)
                    result = client.chat.completions.create(
                        model="gpt-4o",  # مدل دلخواه خودت بذار؛ در نمونه‌ات gpt-4.1-mini هم بود
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt or "این تصویر را تحلیل کن"},
                                {"type": "image_url", "image_url": {"url": data_uri}}
                            ]
                        }],
                        max_tokens=1000
                    )

                    reply = result.choices[0].message.content
                    usage = result.usage

                except Exception as exc:
                    # خطای اختصاصی برای دیباگ
                    return HttpResponse(f"🚫 خطا هنگام ارسال تصویر: {str(exc)}", status=500)




            elif audio:

                try:

                    # 1) فایل صوتی رو به صورت bytes بخون

                    audio_bytes = audio.read()

                    # 2) نام و نوع MIME رو مشخص کن

                    audio_name = getattr(audio, "name", "voice.wav")

                    audio_mime = getattr(audio, "content_type", None) or "audio/wav"

                    # 3) فایل موقت برای پاس دادن به API بساز

                    from io import BytesIO

                    audio_file = BytesIO(audio_bytes)

                    audio_file.name = audio_name  # مهم چون Whisper به پسوند توجه می‌کنه

                    # 4) ارسال به مدل Whisper برای تبدیل گفتار به متن

                    transcript = client.audio.transcriptions.create(

                        model="whisper-1",

                        file=audio_file

                    )

                    prompt_text = transcript.text.strip()

                    # 5) از GPT بپرس: آیا باید تصویر تولید شود؟

                    decision = client.chat.completions.create(

                        model="gpt-4o-mini",

                        messages=[

                            {"role": "system",
                             "content": "تشخیص بده آیا درخواست کاربر نیاز به تولید عکس دارد یا نه. فقط yes یا no جواب بده."},

                            {"role": "user", "content": prompt_text}

                        ],

                        max_tokens=5

                    )

                    decision_text = decision.choices[0].message.content.lower()

                    if "yes" in decision_text:

                        # 6) تولید تصویر

                        img_result = client.images.generate(

                            model="dall-e-3",

                            prompt=prompt_text,

                            size="1024x1024"

                        )

                        img_url = img_result.data[0].url

                        reply = f"🖼️ تصویر ساخته شد:<br><img src='{img_url}' style='max-width:100%;border-radius:12px;box-shadow:0 2px 6px rgba(0,0,0,0.3);'>"

                        usage = {"total_tokens": 0}


                    else:

                        # 7) مسیر عادی → جواب متنی

                        result = client.chat.completions.create(

                            model="gpt-4o-mini",  # یا gpt-4o برای کیفیت بالاتر

                            messages=[{"role": "user", "content": prompt_text}],

                            max_tokens=800

                        )

                        reply = result.choices[0].message.content

                        usage = result.usage


                except Exception as exc:

                    return HttpResponse(f"🚫 خطا هنگام پردازش ویس: {str(exc)}", status=500)




            elif document:
                # همیشه از اول usage رو تعریف کن
                usage = {'total_tokens': 0, 'prompt_tokens': 0, 'completion_tokens': 0}
                reply = "❌ مشکلی پیش آمده است."  # پیش‌فرض اولیه

                try:
                    # گرفتن فایل از request
                    uploaded_file = document  # چون قبلاً از request.FILES پاس دادی

                    # 1) ایجاد Vector Store
                    vector_store = client.beta.vector_stores.create(
                        name=f"user_{user.id}_store"
                    )

                    # 2) آپلود فایل به Vector Store (روش upload_and_poll)
                    file_streams = [uploaded_file]
                    client.beta.vector_stores.file_batches.upload_and_poll(
                        vector_store_id=vector_store.id,
                        files=file_streams
                    )

                    # 3) ساخت Assistant متصل به فایل
                    assistant = client.beta.assistants.create(
                        name="File Chat Assistant",
                        instructions=(
                            "شما یک دستیار حرفه‌ای هستید که باید به پرسش‌های کاربر بر اساس محتوای فایل‌های آپلود شده پاسخ دهید. "
                            "اگر جواب داخل فایل نبود، مودبانه اعلام کنید."
                        ),
                        model="gpt-4o-mini",
                        tools=[{"type": "file_search"}],
                        tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
                    )

                    # 4) ذخیره اطلاعات در سشن
                    chat_session.assistant_id = assistant.id
                    chat_session.vector_store_id = vector_store.id
                    chat_session.save()

                    reply = "✅ فایل شما با موفقیت آپلود شد و حالا می‌توانید با آن چت کنید."

                except Exception as e:
                    reply = f"❌ خطا در پردازش فایل: {str(e)}"
                    usage = {'total_tokens': 0, 'prompt_tokens': 0, 'completion_tokens': 0}

                try:

                    # گرفتن فایل از request

                    uploaded_file = document  # چون قبلاً از request.FILES پاس دادی

                    # 1) ایجاد Vector Store

                    vector_store = client.beta.vector_stores.create(

                        name=f"user_{user.id}_store"

                    )

                    # 2) آپلود فایل به Vector Store (روش upload_and_poll)

                    file_streams = [uploaded_file]  # چون خودش یک فایل باینری از request هست

                    client.beta.vector_stores.file_batches.upload_and_poll(

                        vector_store_id=vector_store.id,

                        files=file_streams

                    )

                    # 3) ساخت Assistant متصل به فایل

                    assistant = client.beta.assistants.create(

                        name="File Chat Assistant",

                        instructions=(

                            "شما یک دستیار حرفه‌ای هستید که باید به پرسش‌های کاربر بر اساس محتوای فایل‌های آپلود شده پاسخ دهید. "
        
                            "اگر جواب داخل فایل نبود، مودبانه اعلام کنید."

                        ),

                        model="gpt-4o-mini",

                        tools=[{"type": "file_search"}],

                        tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}

                    )

                    # 4) ذخیره اطلاعات در سشن

                    chat_session.assistant_id = assistant.id

                    chat_session.vector_store_id = vector_store.id

                    chat_session.save()

                    reply = "✅ فایل شما با موفقیت آپلود شد و حالا می‌توانید با آن چت کنید."

                    usage = {'total_tokens': 0, 'prompt_tokens': 0, 'completion_tokens': 0}


                except Exception as e:

                    reply = f"❌ خطا در پردازش فایل: {str(e)}"

                    usage = None





            else:

                try:

                    # 1) سیستم پیام پایه

                    system_message = {

                        "role": "system",

                        "content": (

                            "شما یک دستیار حرفه‌ای و مودب هستید که به زبان فارسی پاسخ می‌دهید. پاسخ‌ها باید:\n"

                            "- ساختاریافته باشند ✅\n"

                            "- شامل تیترهای برجسته (Bold) برای بخش‌های مختلف باشند 📝\n"

                            "- در صورت نیاز لیست‌وار توضیح داده شوند 🔹\n"

                            "- از علائم نگارشی درست استفاده شود ✍️\n"

                            "- از ایموجی برای زیباتر شدن پاسخ بهره بگیرید 😊\n"

                            "- پاسخ شامل مقدمه، بدنه و جمع‌بندی باشد 📚\n"

                            "پاسخ‌ها باید شبیه خروجی چت‌بات ChatGPT باشند؛ مفصل، خوانا، و با لحن دوستانه و حرفه‌ای.\n"

                            "انگلیسی‌ها رو چپ‌چین کن.\n"

                            "اگر کاربر سؤال کوتاهی پرسید، باز هم پاسخ کامل و توضیح‌دار بده.\n"

                            "بین بخش‌ها فاصله بگذار و تیترها را bold کن با **. متن باید مرتب و خوانا باشد."

                        )

                    }

                    # 2) بررسی هوشمندانه: آیا کاربر درخواست تولید تصویر دارد؟

                    decision = client.chat.completions.create(

                        model="gpt-4o-mini",

                        messages=[

                            {"role": "system",
                             "content": "تشخیص بده آیا درخواست کاربر نیاز به تولید عکس دارد یا نه. فقط yes یا no جواب بده."},

                            {"role": "user", "content": prompt}

                        ],

                        max_tokens=5

                    )

                    decision_text = decision.choices[0].message.content.lower()

                    if "yes" in decision_text:

                        # 3) تولید تصویر

                        img_result = client.images.generate(

                            model="dall-e-3",

                            prompt=prompt,

                            size="1024x1024"

                        )

                        img_url = img_result.data[0].url

                        reply = f"🖼️ تصویر ساخته شد:<br><img src='{img_url}' style='max-width:100%;border-radius:12px;box-shadow:0 2px 6px rgba(0,0,0,0.3);'>"

                        usage = {"total_tokens": 0}



                    else:

                        # 4) مسیر عادی → پیام متنی

                        previous_messages = Message.objects.filter(session=chat_session).order_by('-id')[:10]

                        history = [system_message]

                        for m in reversed(previous_messages):
                            history.append({"role": "user", "content": m.prompt})

                            history.append({"role": "assistant", "content": m.response})

                        # 🔍 اینجا دیگه نیازی به سرچ دستی نیست، ابزار وب سرچ داخلی صدا زده میشه

                        history.append({"role": "user", "content": prompt})

                        result = client.responses.create(

                            model="gpt-4o",  # یا gpt-4o بسته به نیاز

                            tools=[{"type": "web_search"}],

                            input=history,

                            max_output_tokens=1200,

                            temperature=0.7

                        )

                        reply = result.output_text

                        usage = result.usage


                except Exception as e:

                    return HttpResponse(f"🚫 خطا در تحلیل پیام: {str(e)}", status=500)

        except Exception as e:
            return HttpResponse(f"🚫 خطا در پردازش پیام: {str(e)}", status=500)

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