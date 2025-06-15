from django import forms

class UploadForm(forms.Form):
    prompt = forms.CharField(widget=forms.Textarea, required=False)
    image = forms.ImageField(required=False)
    audio = forms.FileField(required=False)
    document = forms.FileField(required=False)
