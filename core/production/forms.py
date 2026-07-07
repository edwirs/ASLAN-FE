from django import forms
from datetime import date

from .models import *

class PlantInventoryImportForm(forms.ModelForm):

    class Meta:
        model = PlantInventoryImport
        fields = [
            'file'
        ]

        widgets = {
            'file': forms.FileInput(
                attrs={
                    'accept': '.xlsx,.xls'
                }
            )
        }

class PlantInventoryFilterForm(forms.Form):

    code = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Código'
        })
    )

    plot_id = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Plot ID'
        })
    )

    location = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Localización'
        })
    )

    genus = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Género'
        })
    )

    area = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Área'
        })
    )