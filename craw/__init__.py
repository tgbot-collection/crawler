#!/usr/local/bin/python3
# coding: utf-8

# crawler - __init__.py.py
# 8/10/21 19:17
#

__author__ = "Benny <benny.think@gmail.com>"

from .tasks_douban import douban_craw
from .tasks_zhuixinfan import zhuixinfan

__all__ = [
    'douban_craw',
    'zhuixinfan'
]
