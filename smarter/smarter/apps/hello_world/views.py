# -*- coding: utf-8 -*-
"""Django views"""
from django.shortcuts import render


def hello_world(request):
    return render(request, "index.html")
