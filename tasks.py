#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - mongodb.py
# 6/16/21 21:18
#

__author__ = "Benny <benny.think@gmail.com>"

import contextlib
import logging
import os
import re
from urllib.parse import unquote

import pymongo
import requests
from bs4 import BeautifulSoup
from celery import Celery
from retry import retry

mongo_host = os.getenv("mongo") or "localhost"
redis = os.getenv("redis") or "localhost"
broker = f"redis://{redis}:6379/0"
app = Celery('craw', broker=broker)

DOUBAN_SEARCH = "https://www.douban.com/search?cat=1002&q={}"
DOUBAN_DETAIL = "https://movie.douban.com/subject/{}/"


class Mongo:
    def __init__(self):
        self.client = pymongo.MongoClient(host=mongo_host, connect=False,
                                          connectTimeoutMS=5000, serverSelectionTimeoutMS=5000)
        self.db = self.client["zimuzu"]

    def __del__(self):
        self.client.close()


class Douban(Mongo):

    @retry(IndexError, tries=3, delay=5)
    def find_douban(self, resource_id: int):
        session = requests.Session()
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
        session.headers.update({"User-Agent": ua})

        douban_col = self.db["douban"]
        yyets_col = self.db["yyets"]
        data = douban_col.find_one({"resourceId": resource_id}, {"_id": False, "raw": False})
        if data:
            logging.info("Existing data for %s", resource_id)
            return data

        projection = {"data.info.cnname": True, "data.info.enname": True, "data.info.aliasname": True}
        names = yyets_col.find_one({"data.info.id": resource_id}, projection=projection)
        if names is None:
            return {}
        cname = names["data"]["info"]["cnname"]
        logging.info("cnname for douban is %s", cname)

        search_html = session.get(DOUBAN_SEARCH.format(cname)).text
        logging.info("Analysis search html...length %s", len(search_html))
        soup = BeautifulSoup(search_html, 'html.parser')
        douban_item = soup.find_all("div", class_="content")

        fwd_link = unquote(douban_item[0].a["href"])
        douban_id = re.findall(r"https://movie.douban.com/subject/(\d*)/&query=", fwd_link)[0]
        final_data = self.get_craw_data(cname, douban_id, resource_id, search_html, session)
        douban_col.insert_one(final_data.copy())
        final_data.pop("raw")
        return final_data

    @staticmethod
    def get_craw_data(cname, douban_id, resource_id, search_html, session):
        detail_link = DOUBAN_DETAIL.format(douban_id)
        detail_html = session.get(detail_link).text
        logging.info("Analysis detail html...%s", detail_link)
        soup = BeautifulSoup(detail_html, 'html.parser')

        directors = [i.text for i in (soup.find_all("a", rel="v:directedBy"))]
        release_date = poster_image_link = rating = year_text = intro = writers = episode_count = episode_duration = ""
        with contextlib.suppress(IndexError):
            episode_duration = soup.find_all("span", property="v:runtime")[0].text
        for i in soup.find_all("span", class_="pl"):
            if i.text == "编剧":
                writers = re.sub(r"\s", "", list(i.next_siblings)[1].text).split("/")
            if i.text == "集数:":
                episode_count = str(i.nextSibling)
            if i.text == "单集片长:" and not episode_duration:
                episode_duration = str(i.nextSibling)
        actors = [i.text for i in soup.find_all("a", rel="v:starring")]
        genre = [i.text for i in soup.find_all("span", property="v:genre")]

        with contextlib.suppress(IndexError):
            release_date = soup.find_all("span", property="v:initialReleaseDate")[0].text
        with contextlib.suppress(IndexError):
            poster_image_link = soup.find_all("div", id="mainpic")[0].a.img["src"]
        with contextlib.suppress(IndexError):
            rating = soup.find_all("strong", class_="ll rating_num")[0].text
        with contextlib.suppress(IndexError):
            year_text = re.sub(r"[()]", "", soup.find_all("span", class_="year")[0].text)
        with contextlib.suppress(IndexError):
            intro = re.sub(r"\s", "", soup.find_all("span", property="v:summary")[0].text)

        final_data = {
            "name": cname,
            "raw": {
                "search_url": DOUBAN_SEARCH.format(cname),
                "detail_url": detail_link,
                "search_html": search_html,
                "detail_html": detail_html
            },
            "doubanId": int(douban_id),
            "doubanLink": detail_link,
            "posterLink": poster_image_link,
            "posterData": session.get(poster_image_link).content,
            "resourceId": resource_id,
            "rating": rating,
            "actors": actors,
            "directors": directors,
            "genre": genre,
            "releaseDate": release_date,
            "episodeCount": episode_count,
            "episodeDuration": episode_duration,
            "writers": writers,
            "year": year_text,
            "introduction": intro
        }
        return final_data


@app.task
def craw(rid: int):
    d = Douban()
    d.find_douban(rid)
