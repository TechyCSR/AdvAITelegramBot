FROM python:3.11-alpine

WORKDIR /AdvAITelegramBot

COPY . /AdvAITelegramBot



RUN apk update \
    &&  apk add --no-cache --virtual .build-deps gcc musl-dev libffi-dev git \
    &&  apk add libffi-dev \
    &&  apk add --no-cache curl-dev \
    &&  apk add --no-cache curl \
    &&  apk add --no-cache libcurl \
    &&  apk add --no-cache libressl \
    && pip install --no-cache-dir -r requirements.txt \ 
    && apk del .build-deps

CMD [ "python", "run.py" ]

EXPOSE 80/tcp

