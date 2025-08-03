# from django import forms
# from .models import AudioFile
#
# class AudioFileForm(forms.ModelForm):
#     class Meta:
#         model = AudioFile
#         fields = ['audio']

from django import forms
from .models import AudioFile

class AudioFileForm(forms.ModelForm):
    class Meta:
        model = AudioFile
        fields = ['audio']
        widgets = {
            'audio': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
