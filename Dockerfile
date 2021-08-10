FROM python:alpine

RUN pip install celery celery[redis] pymongo redis beautifulsoup4 retry requests tqdm
COPY . /APP
WORKDIR /APP

