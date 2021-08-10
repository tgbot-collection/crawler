#!/usr/local/bin/python3
# coding: utf-8

# crawler - tasks.py
# 8/10/21 18:49
#

__author__ = "Benny <benny.think@gmail.com>"

import os

from celery import Celery

redis = os.getenv("redis") or "localhost"
broker = f"redis://{redis}:6379/5"
app = Celery('tasks', broker=broker)

app.autodiscover_tasks(["craw"], force=True)
