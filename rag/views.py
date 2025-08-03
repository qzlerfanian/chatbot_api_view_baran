from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import UploadedFile
from .utils import extract_text_from_pdf, create_chunks_and_embeddings, get_relevant_chunks
import openai
from chatgpt_app.models import TokenUsage
from django.contrib import messages
from openai import OpenAI
from .forms import UploadFileForm
from .forms import NewChatSessionForm
from .models import ChatSessions, ChatMessage
from django.shortcuts import  get_object_or_404


# @login_required
# def upload_file(request):
#     profile = request.user.userprofile
#     if not profile.is_approved:
#         messages.error(request, "دسترسی شما هنوز فعال نشده است.")
#         return redirect('not_approved')
#
#     if request.method == 'POST':
#         form = UploadFileForm(request.POST, request.FILES)
#         if form.is_valid():
#             instance = form.save(commit=False)
#             instance.user = request.user
#             instance.save()
#
#             path = instance.file.path
#             extracted_text = extract_text_from_pdf(path)
#             instance.extracted_text = extracted_text
#             instance.save()
#
#             create_chunks_and_embeddings(instance)
#             messages.success(request, "فایل با موفقیت بارگذاری و پردازش شد.")
#             return redirect('chat_with_session')
#         else:
#             messages.error(request, "فرم معتبر نیست. لطفاً دوباره تلاش کنید.")
#     else:
#         form = UploadFileForm()
#
#     return render(request, 'uploadfile.html', {'form': form})
#

@login_required
def upload_file(request):
    profile = request.user.userprofile
    if not profile.is_approved:
        messages.error(request, "دسترسی شما هنوز فعال نشده است.")
        return redirect('not_approved')

    user_files = UploadedFile.objects.filter(user=request.user).order_by('-uploaded_at').prefetch_related('chat_sessions')

    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.user = request.user
            instance.save()

            path = instance.file.path
            extracted_text = extract_text_from_pdf(path)
            instance.extracted_text = extracted_text
            instance.save()

            create_chunks_and_embeddings(instance)
            messages.success(request, "فایل با موفقیت بارگذاری و پردازش شد.")
            return redirect('create_chat_session', file_id=instance.id)
        else:
            messages.error(request, "فرم معتبر نیست. لطفاً دوباره تلاش کنید.")
    else:
        form = UploadFileForm()

    return render(request, 'uploadfile.html', {
        'form': form,
        'user_files': user_files
    })

@login_required
def create_chat_session(request, file_id):
    uploaded_file = get_object_or_404(UploadedFile, id=file_id, user=request.user)

    if request.method == 'POST':
        form = NewChatSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.uploaded_file = uploaded_file
            session.user = request.user
            session.save()
            return redirect('chat_with_session', session.id)
    else:
        form = NewChatSessionForm()

    return render(request, 'create_session.html', {'form': form, 'file': uploaded_file})
# @login_required
# def ask_question(request):
#     profile = request.user.userprofile
#     if not profile.is_approved:
#         messages.error(request, "دسترسی شما هنوز فعال نشده است.")
#         return redirect('not_approved')
#
#     if request.method == 'POST':
#         question = request.POST['question']
#         chunks = get_relevant_chunks(question, request.user)
#         context = "\n\n".join([chunk.content for chunk in chunks])
#
#         prompt = f"""
# اطلاعات زیر از فایل‌های شما استخراج شده است:
# {context}
#
# سوال: {question}
#         """
#
#         client = OpenAI(
#             api_key='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',
#             timeout=30
#         )  # ← کلید API اینجا قرار می‌گیره یا از env
#
#         response = client.chat.completions.create(
#             model="gpt-4",
#             messages=[{"role": "user", "content": prompt}]
#         )
#
#         answer = response.choices[0].message.content
#         tokens_used = response.usage.total_tokens
#
#         # کم‌کردن توکن
#         profile = request.user.userprofile
#         if profile.token_balance < tokens_used:
#             messages.error(request, "توکن کافی برای این درخواست ندارید.")
#             return redirect('ask_question')
#
#         profile.token_balance -= tokens_used
#         profile.save()
#         TokenUsage.objects.create(user=request.user, tokens=tokens_used)
#
#         return render(request, 'answer.html', {'answer': answer, 'question': question})
#
#     return render(request, 'ask.html')

# @login_required
# def chat_with_session(request, session_id):
#     profile = request.user.userprofile
#     session = get_object_or_404(ChatSessions, id=session_id, user=request.user)
#     uploaded_file = session.uploaded_file
#
#     if not profile.is_approved:
#         messages.error(request, "دسترسی شما هنوز فعال نشده است.")
#         return redirect('not_approved')
#
#     if request.method == 'POST':
#         user_question = request.POST['question'].strip()
#
#         # ذخیره پیام کاربر
#         ChatMessage.objects.create(session=session, sender='user', message=user_question)
#
#         # دریافت context فایل
#         chunks = get_relevant_chunks(user_question, request.user)
#         context_chunks = "\n\n".join([chunk.content for chunk in chunks])
#
#         # آماده‌سازی تاریخچه چت
#         past_messages = session.messages.order_by('timestamp')[:10]
#         gpt_messages = [
#             {"role": "user" if m.sender == 'user' else "assistant", "content": m.message}
#             for m in past_messages
#         ]
#         gpt_messages.append({
#             "role": "user",
#             "content": f"اطلاعات زمینه:\n{context_chunks}\n\nسؤال:\n{user_question}"
#         })
#
#         client = OpenAI(api_key='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',
#  timeout=30)
#         response = client.chat.completions.create(
#             model="gpt-4",
#             messages=gpt_messages
#         )
#         print(response)
#
#         if response.choices:
#             answer = response.choices[0].message.content.strip()
#             tokens_used = response.usage.total_tokens
#             print(answer)
#
#
#             # بررسی موجودی توکن
#             if profile.token_balance < tokens_used:
#                 messages.error(request, "توکن کافی ندارید.")
#                 return redirect('chat_with_session', session_id=session.id)
#
#             # ذخیره در دیتابیس
#             ChatMessage.objects.create(session=session, sender='ai', message=answer)
#             profile.token_balance -= tokens_used
#             profile.save()
#             TokenUsage.objects.create(user=request.user, tokens=tokens_used)
#
#     # لیست کل پیام‌ها
#     messages_ = session.messages.order_by('timestamp')
#     return render(request, 'chat_session.html', {
#         'session': session,
#         'file': uploaded_file,
#         'messages': messages_
#     })

@login_required
def chat_with_session(request, session_id):
    profile = request.user.userprofile
    session = get_object_or_404(ChatSessions, id=session_id, user=request.user)
    uploaded_file = session.uploaded_file

    if not profile.is_approved:
        messages.error(request, "دسترسی شما هنوز فعال نشده است.")
        return redirect('not_approved')

    if request.method == 'POST':
        user_question = request.POST['question'].strip()

        # ذخیره پیام کاربر
        ChatMessage.objects.create(session=session, sender='user', message=user_question)

        # دریافت context فایل
        chunks = get_relevant_chunks(user_question, request.user)
        context_chunks = "\n\n".join([chunk.content for chunk in chunks])

        # آماده‌سازی تاریخچه چت
        past_messages = session.messages.order_by('timestamp')[:10]
        gpt_messages = [
            {"role": "user" if m.sender == 'user' else "assistant", "content": m.message}
            for m in past_messages
        ]
        gpt_messages.append({
            "role": "user",
            "content": f"اطلاعات زمینه:\n{context_chunks}\n\nسؤال:\n{user_question}"
        })

        # بررسی اولیه موجودی توکن (فرض می‌کنیم حداقل 50 توکن لازم است)
        if profile.token_balance < 50:
            messages.error(request, "توکن کافی ندارید.")
            return redirect('chat_with_session', session_id=session.id)

        client = OpenAI(api_key='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',
                        timeout=30)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=gpt_messages
        )
        print(response)

        if response.choices:
            answer = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens
            print(answer)

            # بررسی دقیق‌تر موجودی توکن بعد از دریافت پاسخ
            if profile.token_balance < tokens_used:
                messages.error(request, "توکن کافی برای این پاسخ ندارید.")
                return redirect('chat_with_session', session_id=session.id)

            # ذخیره پاسخ و کسر توکن
            ChatMessage.objects.create(session=session, sender='ai', message=answer)
            profile.token_balance -= tokens_used
            profile.save()
            TokenUsage.objects.create(user=request.user, tokens=tokens_used)

    # لیست کل پیام‌ها
    messages_ = session.messages.order_by('timestamp')
    return render(request, 'chat_session.html', {
        'session': session,
        'file': uploaded_file,
        'messages': messages_
    })

@login_required
def not_approved(request):
    return render(request, 'not_approved.html')

