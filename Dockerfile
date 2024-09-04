FROM python:3.12-slim@sha256:59c7332a4a24373861c4a5f0eec2c92b87e3efeb8ddef011744ef9a751b1d11c AS builder

ARG EXPORT_FLAG=--dev

RUN pip install --upgrade pip poetry

COPY pyproject.toml poetry.toml poetry.lock ./

RUN poetry export -f requirements.txt $EXPORT_FLAG --without-hashes --output /tmp/requirements.txt


FROM python:3.12-slim@sha256:59c7332a4a24373861c4a5f0eec2c92b87e3efeb8ddef011744ef9a751b1d11c

RUN apt-get update && \
  apt upgrade -y

WORKDIR /app

RUN groupadd -g 10000 app && \
  useradd -g app -d /app -u 10000 app && \
  chown app:app /app && \
  apt-get update && \
  apt-get install nano && \
  apt install -y gcc libpq-dev git gettext make postgresql && \
  pip install --upgrade pip

COPY --from=builder /tmp/requirements.txt .

RUN pip install -r requirements.txt

COPY devops-toolbox/scripts/secrets-entrypoint.sh secrets-entrypoint.sh
COPY . .

RUN django-admin compilemessages &&\
    python manage.py spectacular --file assets/schema.yml &&\
    python manage.py collectstatic &&\
    rm -fr /app/assets/*

USER app

EXPOSE 8080

ENTRYPOINT [ "./secrets-entrypoint.sh" ]
