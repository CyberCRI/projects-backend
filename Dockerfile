FROM python:3.13-slim AS builder

ARG EXPORT_FLAG="--all-groups"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./

RUN uv export ${EXPORT_FLAG:+$EXPORT_FLAG} --no-hashes --output-file /tmp/requirements.txt


FROM python:3.13-slim

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

RUN django-admin compilemessages
RUN python manage.py spectacular --file assets/schema.yml
RUN python manage.py collectstatic
RUN rm -fr /app/assets/*

USER app

EXPOSE 8080

ENTRYPOINT [ "./secrets-entrypoint.sh" ]
