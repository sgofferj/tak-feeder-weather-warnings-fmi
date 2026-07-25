FROM python:3.12-alpine

ENV LANG=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV VERSION=20240916205000


WORKDIR /app
COPY requirements.txt ./
RUN apk add --no-cache git && pip install --no-cache-dir -r requirements.txt && apk del git
COPY --chmod=777 *.py ./

CMD [ "/usr/local/bin/python", "/app/feed.py" ]

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=2 \
  CMD test ! -f /tmp/tak-feeder-healthy
