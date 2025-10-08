
from django.shortcuts import render, redirect, get_object_or_404
from .models import FileChat, Message
from .utils import create_vector_store, ask_file
import io
from django.contrib.auth.decorators import login_required

@login_required

def index(request):
    if not request.user.is_authenticated:
        return redirect("login")  # در صورت نیاز

    chats = FileChat.objects.filter(user=request.user).order_by("-created_at")

    if request.method == "POST" and "file" in request.FILES:
        f = request.FILES["file"]
        file_obj = io.BytesIO(f.read())
        file_obj.name = f.name
        file_obj.seek(0)

        vector_id = create_vector_store(file_obj, f.name)
        chat = FileChat.objects.create(
            user=request.user,  # مالک چت فعلی
            name=f.name,
            vector_store_id=vector_id
        )

        return redirect("chat", chat_id=chat.id)

    return render(request, "ragchat/index.html", {"chats": chats, "chat": None})

@login_required

def chat_view(request, chat_id):
    chat = get_object_or_404(FileChat, id=chat_id, user=request.user)
    messages = chat.messages.all().order_by("created_at")
    chats = FileChat.objects.filter(user=request.user).order_by("-created_at")

    if request.method == "POST":
        if "file" in request.FILES:
            f = request.FILES["file"]
            file_obj = io.BytesIO(f.read())
            file_obj.name = f.name
            file_obj.seek(0)
            create_vector_store(file_obj, f.name, vector_store_id=chat.vector_store_id)

            Message.objects.create(
                file_chat=chat,
                role="assistant",
                content=f"فایل {f.name} به چت اضافه شد."
            )
            return redirect("chat", chat_id=chat.id)

        if "question" in request.POST:
            q = request.POST["question"].strip()
            if q:
                Message.objects.create(file_chat=chat, role="user", content=q)
                answer = ask_file(chat.vector_store_id, q)
                Message.objects.create(file_chat=chat, role="assistant", content=answer)
            return redirect("chat", chat_id=chat.id)

    return render(
        request,
        "ragchat/chat.html",
        {"chat": chat, "messages": messages, "chats": chats},
    )
@login_required

def delete_chat(request, chat_id):
    chat = get_object_or_404(FileChat, id=chat_id, user=request.user)
    chat.delete()
    return redirect("index")


