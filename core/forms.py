from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class UserEmailForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'w-full px-4 py-3 bg-gray-50 border-2 border-gray-200 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 transition', 'placeholder': 'seu.email@exemplo.com'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True # Torna o campo de email obrigatório