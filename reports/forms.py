from django.shortcuts import render
from django.http import HttpResponse
from django import forms
from lessons.models import Category, Product


class ClassListForm(forms.Form):
    category = forms.ModelChoiceField(queryset=Category.objects.all())
    day = forms.ChoiceField(choices=[('', '---------')])
    lesson = forms.ModelChoiceField(queryset=Product.objects.none(), required=False)