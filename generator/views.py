import os
from dotenv import load_dotenv
from openai import OpenAI
# # تعریف client فقط یک بار، بیرون از تابع
from django.db.models import Sum
from django.db.models.functions import TruncDay
from django.utils.timezone import now
from datetime import timedelta
import requests
from django.shortcuts import render
from .forms import PromptForm
from .models import GeneratedImage
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required
from chatgpt_app.models import UserProfile, TokenUsage
from django.contrib import messages
import openai


client = openai.OpenAI(api_key= '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'
)

# تعریف client فقط یک بار

# نرخ تبدیل هزینه به توکن
DALL_E_COSTS = {
    "1024x1024": 0.08,
    "1024x1792": 0.12,
    "1792x1024": 0.12,
}
DOLLAR_PER_TOKEN = 0.01  # 1 توکن = 0.01 دلار

def calculate_tokens_for_image(size="1024x1024"):
    cost = DALL_E_COSTS.get(size, 0.08)
    return int(cost / DOLLAR_PER_TOKEN)


@login_required
def generate_image(request):
    image_instance = None

    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        messages.error(request, "پروفایل شما یافت نشد.")
        return render(request, 'generator/form.html', {'form': PromptForm()})

    if not profile.is_approved:
        messages.error(request, "حساب کاربری شما هنوز تأیید نشده است.")
        return render(request, 'generator/form.html', {'form': PromptForm()})

    size = "1024x1024"  # فعلاً ثابت، بعداً می‌تونی از فرم بگیری
    tokens_required = calculate_tokens_for_image(size)

    if profile.token_balance < tokens_required:
        messages.error(request, f"برای تولید تصویر به حداقل {tokens_required} توکن نیاز دارید.")
        return render(request, 'generator/form.html', {'form': PromptForm(), 'token_balance': profile.token_balance})

    if request.method == 'POST':
        form = PromptForm(request.POST)
        if form.is_valid():
            prompt = form.cleaned_data['prompt']

            try:
                response = client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    size=size,
                    n=1
                )

                image_url = response.data[0].url
                image_data = requests.get(image_url).content

                # ذخیره تصویر
                image_instance = GeneratedImage(prompt=prompt, user=request.user)
                image_instance.image.save(f"{prompt[:50]}.png", ContentFile(image_data))
                image_instance.save()

                # کسر توکن و ثبت مصرف
                profile.token_balance -= tokens_required
                profile.save()

                TokenUsage.objects.create(
                    user=request.user,
                    tokens=tokens_required,
                    reason=f"generate_image_{size}"
                )

                messages.success(request, f"{tokens_required} توکن بابت تولید تصویر کسر شد. موجودی فعلی: {profile.token_balance}")

            except Exception as e:
                messages.error(request, f"خطا در تولید تصویر: {e}")

    else:
        form = PromptForm()

    last_usage = TokenUsage.objects.filter(user=request.user).order_by('-created_at').first()

    return render(request, 'generator/form.html', {
        'form': form,
        'image': image_instance,
        'token_balance': profile.token_balance,
        'last_usage': last_usage
    })

# @login_required
# def generate_image(request):
#     image_instance = None
#
#     try:
#         profile = UserProfile.objects.get(user=request.user)
#     except UserProfile.DoesNotExist:
#         messages.error(request, "پروفایل شما یافت نشد.")
#         return render(request, 'generator/form.html', {'form': PromptForm()})
#
#     if not profile.is_approved:
#         messages.error(request, "حساب کاربری شما هنوز تأیید نشده است.")
#         return render(request, 'generator/form.html', {'form': PromptForm()})
#
#     if profile.token_balance <= 0:
#         messages.error(request, "موجودی توکن شما تمام شده است.")
#         return render(request, 'generator/form.html', {'form': PromptForm()})
#
#     if request.method == 'POST':
#         form = PromptForm(request.POST)
#         if form.is_valid():
#             prompt = form.cleaned_data['prompt']
#
#             try:
#                 response = client.images.generate(
#                     model="dall-e-3",
#                     prompt=prompt,
#                     size="1024x1024",
#                     n=1
#                 )
#
#                 image_url = response.data[0].url
#                 image_data = requests.get(image_url).content
#
#                 # ذخیره تصویر
#                 image_instance = GeneratedImage(prompt=prompt, user=request.user)
#                 image_instance.image.save(f"{prompt[:50]}.png", ContentFile(image_data))
#                 image_instance.save()
#
#                 # کسر توکن و ثبت مصرف
#                 profile.token_balance -= 1  # یا هر مقدار مصرفی
#                 profile.save()
#
#                 TokenUsage.objects.create(user=request.user, tokens=1)
#
#             except Exception as e:
#                 messages.error(request, f"خطا در تولید تصویر: {e}")
#
#     else:
#         form = PromptForm()
#
#     return render(request, 'generator/form.html', {'form': form, 'image': image_instance})

