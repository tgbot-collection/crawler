FROM python:alpine

RUN pip install celery celery[redis] pymongo redis beautifulsoup4 retry
COPY . /APP
WORKDIR /APP

CMD ['celery', '-A', 'tasks', 'worker', '--loglevel=info']