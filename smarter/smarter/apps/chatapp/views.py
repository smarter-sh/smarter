# -*- coding: utf-8 -*-
"""Django views"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def chatapp(request):
    return render(request, "index.html")
