from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import UploadedFile, ChatSessions, ChatMessage
from .utils import extract_text_from_pdf, create_chunks_and_embeddings, get_relevant_chunks
from .forms import UploadFileForm, NewChatSessionForm
from chatgpt_app.models import TokenUsage
from openai import OpenAI


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
            instance.name = instance.file.name
            instance.save()

            # پردازش PDF
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

    return render(request, 'create_session.html', {
        'form': form,
        'file': uploaded_file
    })


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
        if not user_question:
            return redirect('chat_with_session', session_id=session.id)

        # پیام کاربر
        ChatMessage.objects.create(session=session, sender='user', message=user_question)

        # گرفتن context مرتبط
        chunks = get_relevant_chunks(user_question, request.user)
        context_chunks = "\n\n".join([chunk.content for chunk in chunks])

        # تاریخچه چت
        past_messages = session.messages.order_by('timestamp')[:10]
        gpt_messages = [
            {"role": "user" if m.sender == 'user' else "assistant", "content": m.message}
            for m in past_messages
        ]
        gpt_messages.append({
            "role": "user",
            "content": f"اطلاعات زمینه:\n{context_chunks}\n\nسؤال:\n{user_question}"
        })

        # چک توکن
        if profile.token_balance < 50:
            messages.error(request, "توکن کافی ندارید.")
            return redirect('chat_with_session', session_id=session.id)

        client = OpenAI(api_key="YOUR_API_KEY", timeout=30)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=gpt_messages
        )

        if response.choices:
            answer = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens

            if profile.token_balance < tokens_used:
                messages.error(request, "توکن کافی برای این پاسخ ندارید.")
                return redirect('chat_with_session', session_id=session.id)

            ChatMessage.objects.create(session=session, sender='ai', message=answer)
            profile.token_balance -= tokens_used
            profile.save()
            TokenUsage.objects.create(user=request.user, tokens=tokens_used)

    messages_ = session.messages.order_by('timestamp')
    return render(request, 'chat_session.html', {
        'session': session,
        'file': uploaded_file,
        'messages': messages_
    })


@login_required
def not_approved(request):
    return render(request, 'not_approved.html')
