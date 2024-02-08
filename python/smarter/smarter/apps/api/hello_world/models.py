# -*- coding: utf-8 -*-
from django.db import models


# Create your models here.
class HelloWorld(models.Model):
    message = models.CharField(max_length=200)
