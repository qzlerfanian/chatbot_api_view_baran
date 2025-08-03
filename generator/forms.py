from django import forms

class PromptForm(forms.Form):
    prompt = forms.CharField(label='توضیح عکس', max_length=255)
