from django import forms
from .models import Photo

class PhotoUploadForm(forms.ModelForm):
    class Meta:
        model = Photo
        fields = ['report', 'image', 'notes']
        widgets = {
            'report': forms.Select(attrs={'class': 'w-full p-3 border border-gray-300 rounded-lg mb-4'}),
            'image': forms.FileInput(attrs={'class': 'w-full p-3 border border-gray-300 rounded-lg mb-4 bg-white'}),
            'notes': forms.Textarea(attrs={'class': 'w-full p-3 border border-gray-300 rounded-lg mb-4', 'rows': 3}),
        }
