from django import forms
from django.contrib.auth import get_user_model
from .models import Candidate, User


class AddCandidateForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    full_name = forms.CharField(max_length=255, required=False)
    source = forms.ChoiceField(choices=Candidate.SOURCE_CHOICES, required=True)
    source_score = forms.IntegerField(min_value=0, required=False, initial=0)
    skills = forms.CharField(widget=forms.Textarea, required=False)

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already in use.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already in use.")
        return email


class CandidateForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = ['skills', 'resume_url', 'interview_status', 'interview_notes']
        widgets = {
            'interview_notes': forms.Textarea(attrs={'rows': 4}),
        }
        exclude = ['user', 'generated_password']


class UserForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ['username', 'email', 'full_name']