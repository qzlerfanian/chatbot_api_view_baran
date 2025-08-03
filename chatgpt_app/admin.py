from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from .models import UserProfile, TokenUsage

# ✅ این کلاس برای نمایش UserProfile در admin
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'پروفایل کاربر'

# ✅ این کلاس برای نمایش کاربر با اطلاعات اضافی
class CustomUserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = ('username', 'email', 'is_active', 'is_staff', 'is_approved_display')
    actions = ['approve_users', 'renew_tokens']

    def is_approved_display(self, obj):
        try:
            return obj.userprofile.is_approved
        except UserProfile.DoesNotExist:
            return format_html('<span style="color:red;">❌ ندارد</span>')
    is_approved_display.short_description = "تأیید شده؟"
    # ✅ تایید اولیه
    def approve_users(self, request, queryset):
        for user in queryset:
            profile = user.userprofile
            if not profile.is_approved:
                profile.is_approved = True
                profile.save()

            already_given = TokenUsage.objects.filter(user=user).exists()
            if not already_given:
                TokenUsage.objects.create(user=user, tokens=10000000)
                profile.token_balance += 10000000
                profile.save()
        self.message_user(request, "✅ کاربران تایید شدند و 10000000 توکن دریافت کردند.")

    # ✅ تمدید توکن
    def renew_tokens(self, request, queryset):
        for user in queryset:
            profile = user.userprofile
            TokenUsage.objects.create(user=user, tokens=5000000)
            profile.token_balance += 5000000
            profile.save()
        self.message_user(request, "🔁 توکن کاربران تمدید شد (5000000 توکن اضافه شد).")
    renew_tokens.short_description = "تمدید توکن کاربران (5000000 توکن)"


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
