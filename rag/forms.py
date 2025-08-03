from django import forms
from .models import UploadedFile
from .models import ChatSessions

class UploadFileForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ['file']
        widgets = {
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class QuestionForm(forms.Form):
    question = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}))


class NewChatSessionForm(forms.ModelForm):
    class Meta:
        model = ChatSessions
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'عنوان گفتگو'}),
        }
