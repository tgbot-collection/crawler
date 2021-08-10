#!/usr/local/bin/python3
# coding: utf-8

# untitled - zhui.py
# 8/10/21 08:58
#

__author__ = "Benny <benny.think@gmail.com>"

import logging
import os
import random
import re
import sys
import time

import pymongo
import requests
from bs4 import BeautifulSoup

from tasks import app

mongo_host = os.getenv("mongo") or "localhost"

logging.basicConfig(level=logging.INFO)


def get_way(link) -> (str, str):
    if "baidu" in link:
        return "100", "百度网盘"
    if "weiyun" in link:
        return "101", "微云"


def get_default_format():
    db_format = {
        "status": 1,
        "info": "OK",
        "data": {
            "info": {
                "id": 99999,
                "source": "zhuixinfan",
                "cnname": "",
                "enname": "",
                "aliasname": "",
                "channel": "",
                "channel_cn": "",
                "area": "日本",
                "show_type": "",
                "expire": "1610401225",
                "views": 0
            },
            "list": [
                {
                    "season_num": "1",
                    "season_cn": "第1季",
                    "items": {
                        "MP4": [

                        ]
                    },
                    "formats": [
                        "MP4"
                    ]
                }
            ]
        }
    }
    return db_format


def analysis_zhuixinfan(detail_html):
    logging.info("analysing html")

    db_format = get_default_format()
    soup = BeautifulSoup(detail_html, 'html.parser')

    title = soup.findAll("h2")[0].text
    cnname = soup.title.text.split("_")[0]

    enname = re.sub(r"\(\d*\)", "", title.replace(cnname, "")).strip()
    year = re.findall(r"(\d+)", title)[0]

    remark = soup.find("p", class_="remark")
    channel_cn, channel = "日剧", "tv"
    if "日剧" in remark.text:
        channel_cn = "日剧"
        channel = "tv"

    db_format["data"]["info"]["channel"] = channel_cn
    db_format["data"]["info"]["channel_cn"] = channel
    db_format["data"]["info"]["cnname"] = cnname
    db_format["data"]["info"]["enname"] = enname

    links = soup.find("ul", class_="item_list").find_all("li")
    for link in links:
        episode = link.p.span.text
        episode = re.sub(r"S\d\dE", "", episode)
        filename = link.p.span.next_sibling.text
        files = []
        for p in link.p.next_siblings:
            for span in p:
                address, passwd = "", ""
                for a_link in span.find_all("a"):
                    if a_link.attrs.get("class") == ["password"]:
                        passwd = a_link.text
                    else:
                        address = a_link["href"]

                way, way_cn = get_way(address)

                files.append(
                    {
                        "way": way,
                        "way_cn": way_cn,
                        "address": address,
                        "passwd": passwd
                    }
                )

            db_format["data"]["list"][0]["items"]["MP4"].append(
                {
                    "itemid": "",
                    "episode": episode,
                    "name": filename,
                    "size": "unknown",
                    "yyets_trans": 0,
                    "dateline": "{}".format(int(time.time())),
                    "files": files
                }
            )
    return db_format


def get_analysis_data(url):
    logging.info("requesting to %s", url)
    r = requests.get(url)
    html_text = r.content.decode("u8")
    if "资源不存在" not in html_text:
        data = analysis_zhuixinfan(html_text)
        # add url
        data["data"]["list"][0]["items"]["MP4"].insert(0,
                                                       {
                                                           "itemid": "",
                                                           "episode": "追新番",
                                                           "name": "追新番链接",
                                                           "size": "unknown",
                                                           "yyets_trans": 0,
                                                           "dateline": "{}".format(int(time.time())),
                                                           "files": [{
                                                               "way": "321",
                                                               "way_cn": "外链",
                                                               "address": url,
                                                               "passwd": ""
                                                           }]
                                                       }
                                                       )
        return data
    # with open("resource.html") as f:
    #     detail_html = f.read()
    # return detail_html


@app.task
def zhuixinfan(url):
    data = get_analysis_data(url)
    if data:
        logging.info("data found or %s", url)
        save_to_db(data)


def save_to_db(data):
    rid = get_appropriate_id()
    data["data"]["info"]["id"] = rid
    logging.info("resource id is %s", rid)
    client = pymongo.MongoClient(host=mongo_host, connect=False,
                                 connectTimeoutMS=5000, serverSelectionTimeoutMS=5000)
    col = client["zimuzu"]["yyets"]
    logging.info("Inserting data...%s", sys.getsizeof(data["data"]))
    col.insert_one(data)
    # col.update_one({"data.info.id": rid}, data, upsert=True)


def get_appropriate_id():
    client = pymongo.MongoClient(host=mongo_host, connect=False,
                                 connectTimeoutMS=5000, serverSelectionTimeoutMS=5000)
    col = client["zimuzu"]["yyets"]
    random_id = random.randint(50000, 55000)
    data = col.find_one({"data.info.id": random_id}, projection={"_id": True})
    if data:
        return get_appropriate_id()
    else:
        return random_id


def update_zhuixinfan():
    # TODO...
    pass


if __name__ == '__main__':
    zhuixinfan("http://www.fanxinzhui.com/rr/90")
