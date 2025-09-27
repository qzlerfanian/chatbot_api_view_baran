from django import forms

class PromptForm(forms.Form):
    prompt = forms.CharField(label='توضیح عکس', max_length=255)

class ImageForm(forms.Form):
    image = forms.ImageField(required=True)
    task = forms.ChoiceField(
        choices=[("analyze", "تحلیل تصویر"), ("edit", "ویرایش تصویر"), ("generate", "تولید تصویر جدید")]
    )
    prompt = forms.CharField(required=False, widget=forms.Textarea, help_text="دستور برای GPT یا ویرایش")
