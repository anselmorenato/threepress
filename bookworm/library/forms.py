from django import forms
from models import UserPref

class EpubValidateForm(forms.Form):
    epub = forms.FileField()

class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserPref
        exclude = ('user', 'created_time','username', 'country', 'language')
