from django import forms
from datetime import date

from .models import *


class BiologicalTargetCategoryForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['autofocus'] = True

    class Meta:
        model = BiologicalTargetCategory
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Ingrese un nombre'}),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'cols': 3,
                'placeholder': 'Ingrese una descripción'
            }),
        }

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

class BiologicalTargetForm(forms.ModelForm):

    class Meta:
        model = BiologicalTarget
        fields = '__all__'

        widgets = {
            'category': forms.Select(
                attrs={
                    'class': 'form-select'
                }
            ),
            'code': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese el código'
                }
            ),
            'name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese el nombre'
                }
            ),
            'scientific_name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese el nombre científico'
                }
            ),

            'healthy_bed': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
            'aspirated': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
            'exclude_aspirated': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
            'external_trap': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
            'internal_trap': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
            'cold_room_assurance': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
            'automatic_discard': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
            'is_active': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
        }

    def save(self, commit=True):
        data = {}

        try:
            if self.is_valid():
                instance = super().save()
                data = instance.toJSON()
            else:
                data['error'] = self.errors

        except Exception as e:
            data['error'] = str(e)

        return data

class SeverityGradeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtramos para mostrar solo categorías activas en el select
        self.fields['category'].queryset = BiologicalTargetCategory.objects.filter(is_active=True)
        # Autofocus en el primer campo de selección
        self.fields['category'].widget.attrs['autofocus'] = True

    class Meta:
        model = SeverityGrade
        fields = '__all__'
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select select2'}),
            'grade_number': forms.NumberInput(attrs={
                'min': 1, 
                'max': 10, 
                'placeholder': 'Ej. 1'
            }),
            'name': forms.TextInput(attrs={'placeholder': 'Ej. Grado 1 o Leve'}),
            'min_value': forms.NumberInput(attrs={
                'step': '0.01', 
                'placeholder': 'Límite inferior (ej. 0.00 o 4.00)'
            }),
            'max_value': forms.NumberInput(attrs={
                'step': '0.01', 
                'placeholder': 'Límite superior (ej. 3.00 o 25.00)'
            }),
            'description': forms.TextInput(attrs={'placeholder': 'Ej. 0 a 3 insectos o 0 - 25%'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

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

class MipeModuleForm(forms.ModelForm):

    class Meta:
        model = MipeModule
        fields = '__all__'

        widgets = {

            'name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese el nombre del módulo'
                }
            ),

            'order': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': 1
                }
            ),

            'icon': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'fas fa-search'
                }
            ),

            'is_active': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input'
                }
            ),
        }

    def save(self, commit=True):
        data = {}
        try:
            if self.is_valid():
                instance = super().save(commit=commit)
                data = instance.toJSON()
            else:
                data['error'] = self.errors

        except Exception as e:
            data['error'] = str(e)

        return data

from django import forms


class BlockStructureForm(forms.Form):

    code = forms.CharField(
        max_length=20,
        label='Código',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Ej: B01'
            }
        )
    )

    name = forms.CharField(
        max_length=100,
        label='Nombre',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Bloque 1'
            }
        )
    )

    has_sides = forms.BooleanField(
        required=False,
        label='¿Maneja lado A y B?',
        widget=forms.CheckboxInput(
            attrs={
                'class': 'form-check-input'
            }
        )
    )

    bay_quantity = forms.IntegerField(
        min_value=1,
        label='Cantidad de naves',
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control'
            }
        )
    )

    bed_quantity = forms.IntegerField(
        min_value=1,
        label='Camas por nave',
        initial=8,
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control'
            }
        )
    )

    section_quantity = forms.IntegerField(
        min_value=1,
        label='Cuadros por cama',
        initial=4,
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control'
            }
        )
    )
