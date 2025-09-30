# from django.shortcuts import render, redirect, get_object_or_404
# from .models import FileChat, Message
# from .forms import UploadFileForm
# from .utils import create_vector_store, ask_file
# import io
#
# def index(request):
#     """
#     صفحه اصلی: لیست چت‌ها
#     """
#     chats = FileChat.objects.all().order_by("-created_at")
#     return render(request, "ragchat/index.html", {"chats": chats, "chat": None})
#
#
# def chat_view(request, chat_id):
#     """
#     نمایش یک چت مشخص
#     و امکان اضافه کردن فایل یا پرسش جدید در همان چت
#     """
#     chat = get_object_or_404(FileChat, id=chat_id)
#     messages = chat.messages.all().order_by("created_at")
#     chats = FileChat.objects.all().order_by("-created_at")  # برای سایدبار
#
#     if request.method == "POST":
#         # === آپلود فایل جدید به همان چت ===
#         if "file" in request.FILES:
#             f = request.FILES["file"]
#             file_obj = io.BytesIO(f.read())
#             file_obj.name = f.name
#
#             # آپلود به vector store موجود
#             create_vector_store(file_obj, f.name, vector_store_id=chat.vector_store_id)
#             # Optional: پیام سیستم اضافه کن که فایل آپلود شد
#             Message.objects.create(
#                 file_chat=chat,
#                 role="assistant",
#                 content=f"فایل {f.name} به چت اضافه شد."
#             )
#             return redirect("chat", chat_id=chat.id)
#
#         # === پرسش جدید ===
#         if "question" in request.POST:
#             q = request.POST["question"].strip()
#             if q:
#                 Message.objects.create(file_chat=chat, role="user", content=q)
#                 answer = ask_file(chat.vector_store_id, q)
#                 Message.objects.create(file_chat=chat, role="assistant", content=answer)
#             return redirect("chat", chat_id=chat.id)
#
#     return render(
#         request,
#         "ragchat/chat.html",
#         {"chat": chat, "messages": messages, "chats": chats},
#     )
#
#
# def create_chat(request):
#     """
#     ساخت یک چت جدید با فایل از صفحه اصلی
#     """
#     if request.method == "POST" and "file" in request.FILES:
#         f = request.FILES["file"]
#         file_obj = io.BytesIO(f.read())
#         file_obj.name = f.name
#
#         vector_id = create_vector_store(file_obj, f.name)  # Vector store جدید
#         chat = FileChat.objects.create(name=f.name, vector_store_id=vector_id)
#         return redirect("chat", chat_id=chat.id)
#
#     return redirect("index")
#
#
# def delete_chat(request, chat_id):
#     """
#     حذف یک چت
#     """
#     chat = get_object_or_404(FileChat, id=chat_id)
#     chat.delete()
#     return redirect("index")

from django.shortcuts import render, redirect, get_object_or_404
from .models import FileChat, Message
from .utils import create_vector_store, ask_file
import io

def index(request):
    """
    صفحه اصلی: لیست چت‌ها و آپلود فایل جدید برای ایجاد چت
    """
    chats = FileChat.objects.all().order_by("-created_at")

    if request.method == "POST" and "file" in request.FILES:
        f = request.FILES["file"]
        file_obj = io.BytesIO(f.read())
        file_obj.name = f.name

        # ایجاد vector store جدید و چت جدید
        vector_id = create_vector_store(file_obj, f.name)
        chat = FileChat.objects.create(name=f.name, vector_store_id=vector_id)

        # ریدایرکت مستقیم به صفحه چت همان فایل
        return redirect("chat", chat_id=chat.id)

    return render(request, "ragchat/index.html", {"chats": chats, "chat": None})


def chat_view(request, chat_id):
    """
    نمایش چت مشخص، آپلود فایل به همان چت و پرسش جدید
    """
    chat = get_object_or_404(FileChat, id=chat_id)
    messages = chat.messages.all().order_by("created_at")
    chats = FileChat.objects.all().order_by("-created_at")  # برای سایدبار

    if request.method == "POST":
        # === آپلود فایل جدید به همان چت ===
        if "file" in request.FILES:
            f = request.FILES["file"]
            file_obj = io.BytesIO(f.read())
            file_obj.name = f.name

            # آپلود فایل به vector store موجود
            create_vector_store(file_obj, f.name, vector_store_id=chat.vector_store_id)

            # پیام سیستم برای اطلاع کاربر
            Message.objects.create(
                file_chat=chat,
                role="assistant",
                content=f"فایل {f.name} به چت اضافه شد."
            )
            return redirect("chat", chat_id=chat.id)

        # === پرسش جدید ===
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
        {"chat": chat, "messages": messages, "chats": chats},  # سایدبار همیشه
    )


def delete_chat(request, chat_id):
    """
    حذف یک چت
    """
    chat = get_object_or_404(FileChat, id=chat_id)
    chat.delete()
    return redirect("index")
