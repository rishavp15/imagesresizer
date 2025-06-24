from django import forms
from django.forms import formset_factory
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Div, Field
from crispy_forms.bootstrap import InlineRadios

class BulkImageProcessingForm(forms.Form):
    """Form for handling multiple image uploads (pixels/cm/inch)"""
    
    def __init__(self, *args, **kwargs):
        num_images = kwargs.pop('num_images', 5)
        super().__init__(*args, **kwargs)
        
        for i in range(num_images):
            self.fields[f'image_{i}'] = forms.ImageField(
                required=False,
                widget=forms.FileInput(attrs={
                    'class': 'form-control image-upload-input',
                    'accept': 'image/*',
                    'data-index': i
                })
            )
            self.fields[f'dimension_unit_{i}'] = forms.ChoiceField(
                choices=[('pixels', 'Pixels'), ('cm', 'Centimeters'), ('inch', 'Inches')],
                initial='pixels',
                required=False,
                widget=forms.Select(attrs={
                    'class': 'form-select dimension-unit-selector',
                    'data-index': i
                })
            )
            self.fields[f'output_width_{i}'] = forms.IntegerField(
                required=False,
                min_value=1,
                widget=forms.NumberInput(attrs={
                    'class': 'form-control',
                    'placeholder': 'Width',
                    'data-index': i
                })
            )
            self.fields[f'output_height_{i}'] = forms.IntegerField(
                required=False,
                min_value=1,
                widget=forms.NumberInput(attrs={
                    'class': 'form-control',
                    'placeholder': 'Height',
                    'data-index': i
                })
            )
            self.fields[f'cm_width_{i}'] = forms.FloatField(
                required=False,
                widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'e.g. 10.0', 'data-index': i})
            )
            self.fields[f'cm_height_{i}'] = forms.FloatField(
                required=False,
                widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'e.g. 15.0', 'data-index': i})
            )
            self.fields[f'inch_width_{i}'] = forms.FloatField(
                required=False,
                widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'e.g. 4.0', 'data-index': i})
            )
            self.fields[f'inch_height_{i}'] = forms.FloatField(
                required=False,
                widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'e.g. 6.0', 'data-index': i})
            )
            self.fields[f'dpi_{i}'] = forms.IntegerField(
                required=False,
                min_value=72,
                max_value=600,
                widget=forms.NumberInput(attrs={
                    'class': 'form-control',
                    'data-index': i,
                    'placeholder': '300'
                })
            )
            self.fields[f'target_file_size_kb_{i}'] = forms.IntegerField(
                required=False,
                min_value=5,
                max_value=10240,
                widget=forms.HiddenInput(attrs={
                    'data-index': i
                })
            )
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.form_id = 'bulk-image-form'
        self.helper.form_class = 'needs-validation'
        self.helper.disable_csrf = False 