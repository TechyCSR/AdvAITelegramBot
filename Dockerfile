FROM python:3.11-alpine

WORKDIR /AdvAITelegramBot

COPY . /AdvAITelegramBot

# Enable the edge repository temporarily
RUN echo "http://dl-cdn.alpinelinux.org/alpine/edge/community" >> /etc/apk/repositories \
    && apk update \
    && apk add --no-cache --virtual .build-deps gcc musl-dev libffi-dev git \
    && apk add libffi-dev \
    && apk add --no-cache curl-dev \
    && apk add --no-cache curl \
    && apk add --no-cache libcurl \
    && apk add --no-cache libressl \
    && apk add --no-cache libsndfile \
    && pip install --no-cache-dir -r requirements.txt \ 
    && apk del .build-deps \
    && sed -i '/edge\/community/d' /etc/apk/repositories

CMD ["python", "run.py"]
