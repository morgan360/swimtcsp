from django.shortcuts import render
from .lessons_cart import Cart


def cart(request):
    return {'classes_cart': Cart(request)}
