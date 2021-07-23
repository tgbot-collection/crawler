#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - douban.py
# 7/11/21 10:17
#

__author__ = "Benny <benny.think@gmail.com>"

import contextlib
import logging

from tqdm import tqdm
from tasks import Mongo, craw

logging.basicConfig(level=logging.INFO)


def sync_douban():
    m = Mongo()
    yyets_data = m.db["yyets"].find()
    douban_data = m.db["douban"].find()

    id1 = [i["data"]["info"]["id"] for i in yyets_data]
    id2 = [i["resourceId"] for i in douban_data]
    rids = list(set(id1).difference(id2))
    logging.info("resource id complete %d", len(rids))
    for rid in tqdm(rids):
        with contextlib.suppress(Exception):
            craw.delay(rid)
            logging.info("Submitted %s", rid)

    logging.info("Tasks have been submitted.")


if __name__ == '__main__':
    sync_douban()
