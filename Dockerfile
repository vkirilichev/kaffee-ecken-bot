############################################################
# Dockerfile to run @KaffeeEckenBot
# Based on Python 3.6-alpine Image
############################################################

FROM python:3.6-alpine

MAINTAINER Vasily Kirilichev "https://github.com/vkirilichev"

RUN apk add g++ gcc python-dev libxml2-dev libxslt-dev --update
RUN pip3 install lxml pymongo python-telegram-bot requests

COPY ./bot.py /
ENTRYPOINT python3 ./bot.py $TOKEN
