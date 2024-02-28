# -*- coding: utf-8 -*-
"""Django views"""
from django.shortcuts import render


def chatapp(request):
    return render(request, "index.html")
