from crum import get_current_request
from django import forms
from django.contrib.auth import update_session_auth_hash

from core.pos.images import USER_MAX_SIDE, ProductImageField, shrink_image

from .models import User


class UserImageMixin:
    """Valida la foto del usuario y la reduce (máx. 256 px, WebP): solo se ve pequeña en el menú lateral."""

    def clean_image(self):
        from django.core.files.uploadedfile import UploadedFile
        image = self.cleaned_data.get('image')
        if isinstance(image, UploadedFile):
            return shrink_image(image, max_side=USER_MAX_SIDE)
        return image


class UserForm(UserImageMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['groups'].required = True
        self.fields['groups'].label = 'Roles'
        self.fields['names'].widget.attrs['autofocus'] = True

    class Meta:
        model = User
        fields = 'names', 'username', 'password', 'image', 'email', 'groups', 'is_active'
        widgets = {
            'names': forms.TextInput(attrs={'placeholder': 'Ingrese sus nombres'}),
            'username': forms.TextInput(attrs={'placeholder': 'Ingrese un username'}),
            'email': forms.TextInput(attrs={'placeholder': 'Ingrese su correo electrónico'}),
            'password': forms.PasswordInput(render_value=True, attrs={'placeholder': 'Ingrese un password'}),
            'groups': forms.SelectMultiple(attrs={'class': 'select2', 'multiple': 'multiple', 'style': 'width:100%'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'image': forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'}),
        }
        field_classes = {'image': ProductImageField}
        exclude = ['is_change_password', 'is_staff', 'user_permissions', 'date_joined', 'last_login', 'is_superuser', 'email_reset_token']

    def update_session(self, user):
        request = get_current_request()
        if user == request.user:
            update_session_auth_hash(request, user)

    def save(self, commit=True):
        data = {}
        form = super()
        try:
            if form.is_valid():
                password = self.cleaned_data['password']
                user_form = form.save(commit=False)
                if user_form.pk is None:
                    user_form.set_password(password)
                else:
                    user = User.objects.get(pk=user_form.pk)
                    if user.password != password:
                        user_form.set_password(password)
                user_form.save()
                user_form.groups.clear()
                for i in self.cleaned_data['groups']:
                    user_form.groups.add(i)
                self.update_session(user_form)
            else:
                data['error'] = form.errors
        except Exception as e:
            data['error'] = str(e)
        return data


class ProfileForm(UserImageMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['names'].widget.attrs['autofocus'] = True

    class Meta:
        model = User
        fields = 'names', 'username', 'email', 'image'
        widgets = {
            'names': forms.TextInput(attrs={'placeholder': 'Ingrese sus nombres'}),
            'username': forms.TextInput(attrs={'placeholder': 'Ingrese un username'}),
            'email': forms.TextInput(attrs={'placeholder': 'Ingrese su correo electrónico'}),
            'image': forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'}),
        }
        field_classes = {'image': ProductImageField}
        exclude = ['is_change_password', 'is_active', 'is_staff', 'user_permissions', 'password', 'date_joined', 'last_login', 'is_superuser', 'groups', 'email_reset_token']

    def save(self, commit=True):
        data = {}
        try:
            if self.is_valid():
                super().save()
            else:
                data['error'] = self.errors
        except Exception as e:
            data['error'] = str(e)
        return data


