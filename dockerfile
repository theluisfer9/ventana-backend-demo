FROM python:3.11.9

WORKDIR /usr/src/apikit
COPY ./api ./api
COPY requirements.txt requirements.txt
COPY main.py main.py
COPY .env .env

RUN pip3 install -r requirements.txt