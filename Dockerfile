FROM python:3.13-slim AS builder

ARG EXPORT_FLAG="--all-groups"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./

RUN uv export ${EXPORT_FLAG:+$EXPORT_FLAG} --no-hashes --no-emit-project --output-file /tmp/requirements.txt


FROM python:3.13-slim

RUN apt-get update && \
  apt upgrade -y

# Distrust the compromised eMudhra/emSign roots until Debian ships a patched ca-certificates
# TODO : Remove when fix is published
RUN sed -i -e 's|^mozilla/emSign_ECC_Root_CA_-_G3.crt|!&|' -e 's|^mozilla/Comodo_AAA_Services_root.crt|!&|' /etc/ca-certificates.conf && \
  update-ca-certificates

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
