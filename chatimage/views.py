import base64
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

if OpenAI:
    client = OpenAI(api_key= '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')
else:
    client = None
# نگهداری وضعیت گفتگو در حافظه (ساده)
chat_history = []


def encode_image(image_file):
    return base64.b64encode(image_file.read()).decode("utf-8")


@csrf_exempt
def index(request):
    return render(request, "chatimage/index.html")


@csrf_exempt
def upload_image(request):
    global chat_history
    chat_history = []  # شروع گفتگو جدید

    if request.method == "POST" and request.FILES.get("image"):
        img_file = request.FILES["image"]
        base64_img = encode_image(img_file)

        # اولین پیام کاربر همراه عکس
        chat_history.append({
            "role": "user",
            "content": [
                {"type": "text", "text": "این تصویر را توصیف کن."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}},
            ]
        })

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=chat_history,
        )

        answer = response.choices[0].message.content
        chat_history.append({"role": "assistant", "content": answer})

        return JsonResponse({"answer": answer})
    return JsonResponse({"error": "هیچ عکسی ارسال نشد"}, status=400)


@csrf_exempt
def ask(request):
    global chat_history
    if request.method == "POST":
        question = request.POST.get("question")
        chat_history.append({"role": "user", "content": question})

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=chat_history,
        )

        answer = response.choices[0].message.content
        chat_history.append({"role": "assistant", "content": answer})
        return JsonResponse({"answer": answer})
    return JsonResponse({"error": "درخواست نامعتبر"}, status=400)
