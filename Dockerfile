FROM python:3.6

ADD ./requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
ADD . /app

WORKDIR /app
CMD python -m et_discord_bot
