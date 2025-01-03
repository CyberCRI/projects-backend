# Enable parallel execution
# 3 is the max parallel processes needed so far (for prestart)
MAKEFLAGS += -j3

.PHONY: local
local:
	docker compose up

.PHONY: build
build:
	docker compose build

.PHONY: bash
bash:
	docker exec -it projects bash

.PHONY: fullstack
fullstack:
	docker exec -it projects-backend bash

.PHONY: format
format:
	isort .
	black .

.PHONY: format-check
format-check:
	isort . -c
	black --check .

DJANGO_CHECK_FAIL_LEVEL ?= WARNING
.PHONY: check
check:
# Checks for issues before starting
	python manage.py check --deploy --fail-level="${DJANGO_CHECK_FAIL_LEVEL}"

.PHONY: makemessages
makemessages:
# Create translation files
	python manage.py makemessages --all

.PHONY: algolia-reindex
algolia-reindex:
# Reindex algolia
	python manage.py algolia_reindex

TEMP_TRANSLATION_FILES := $(shell mktemp -d --suffix -projects-back-makemessages)
.PHONY: makemessages-check
makemessages-check:
# Copy translation files to a temp directory
	mkdir -p ${TEMP_TRANSLATION_FILES}/current ${TEMP_TRANSLATION_FILES}/new
	for trans_file in $(shell find locale/ -name '*.po'); do cp -r "$$trans_file" ${TEMP_TRANSLATION_FILES}/current/${trans_file}; done
# Create translation files
	python manage.py makemessages --all
	for trans_file in $(shell find locale/ -name '*.po'); do cp -r "$$trans_file" ${TEMP_TRANSLATION_FILES}/new/${trans_file}; done
# Compare generated translation files with the originals
	diff -r -I "POT-Creation-Date: .*" ${TEMP_TRANSLATION_FILES}/current ${TEMP_TRANSLATION_FILES}/new
# Cleanup
	rm -rf ${TEMP_TRANSLATION_FILES}

.PHONY: collectstatic
collectstatic:
# Collect statics to static/
	python manage.py collectstatic --no-input --skip-checks

.PHONY: migrate
migrate:
# Run the database migrations
	python manage.py migrate --no-input --skip-checks

.PHONY: prestart
prestart: check post-deploy

.PHONY: prestart-no-migrate
prestart-no-migrate: check

.PHONY: start
start:
	gunicorn --config ./gunicorn.conf.py projects.wsgi:application

.PHONY: start-uvicorn
start-uvicorn:
	uvicorn projects.asgi:application --workers 1 --host 0.0.0.0

.PHONY: bandit
bandit:
	bandit -c pyproject.toml -r apps/ projects/

.PHONY: flake8
flake8:
	flake8 .

.PHONY: lint
lint: flake8 bandit

.PHONY: test
test:
	coverage run
	coverage report

.PHONY: dropdb
dropdb:
	./scripts/drop_db.sh

.PHONY: createdb
createdb:
	./scripts/create_db.sh

.PHONY: check-migrations
check-migrations:
	python manage.py makemigrations --noinput --check

.PHONY: post-deploy
post-deploy:
	python manage.py post_deploy
