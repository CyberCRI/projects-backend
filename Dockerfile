FROM python:3.10-slim AS builder

ARG EXPORT_FLAG=

RUN pip install --upgrade pip poetry

COPY pyproject.toml poetry.toml poetry.lock ./

RUN poetry export -f requirements.txt $EXPORT_FLAG --without-hashes --output /tmp/requirements.txt


FROM python:3.10-slim

RUN apt-get update && \
  apt upgrade -y

WORKDIR /app

RUN groupadd -g 10000 app && \
  useradd -g app -d /app -u 10000 app && \
  chown app:app /app && \
  apt-get update && \
  apt install -y gcc libpq-dev git gettext make && \
  pip install --upgrade pip

COPY --from=builder /tmp/requirements.txt .

RUN pip install -r requirements.txt

COPY devops-toolbox/scripts/secrets-entrypoint.sh secrets-entrypoint.sh
COPY . .

RUN django-admin compilemessages

RUN python manage.py collectstatic

USER app

EXPOSE 8080

ENTRYPOINT [ "./secrets-entrypoint.sh" ]
