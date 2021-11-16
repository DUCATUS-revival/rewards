FROM python:3.9.7

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

ENV TORTOISE_ORM=rewards.settings.TORTOISE_ORM

COPY . /app
