# projects-back

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A fresh, clean and well documented framework for helping organizations to manage and communicate on their [research|student|education|any] projects efficiciently.

We are currently supporting two ways of working on this project : using Docker and without.

Please clone the repository first.

```bash
git clone https://github.com/CyberCRI/projects-back.git
cd projects-back
```

## Using Docker

### Requirements
- Docker
- Docker Compose V2

### Run the stack
```bash
make
```

### Migrate the database
*The stack need to be running.*
```bash
make bash
python manage.py migrate
```
### Seed the database
*The stack need to be running.*
```bash
make bash
python manage.py seed_db
```

And you're good to go !

## Without Docker

### Pre-requisite

- Python 3.10 ^
- [Poetry](https://python-poetry.org/docs/#installation)
- [PostgreSQL](https://www.postgresql.org/download/)

First clone the project and move at it:

Switch environment and install dependencies via poetry:

```bash
poetry env use 3.10
poetry install
```

### Django project

Now you have to setup Django, all Django functionalities are available with the `python manage.py` command.

First of all, you should enter your database settings as stated in `projects/settings.py` variable `DATABASES`.

Then initialize your database:

```bash
python manage.py makemigrations # if migrations are not up to date
python manage.py migrate
python manage.py collectstatic
```

### MJML

Projects uses MJML as templating framework for email. We use our own MJML http server to avoid having to install the command line:

```bash
docker-compose up -d mjml
```

## Run the server

You can run the server via the command:

```bash
python manage.py runserver <url>:<port>
```

Where `<url>` can be `localhost` for development purpose.

## Pagination: Limits and offset

Pagination is set in settings in value `DEFAULT_PAGINATION_CLASS` based
on [django-rest-framework documentation](https://www.django-rest-framework.org/api-guide/pagination/#limitoffsetpagination)
to limits and offset. For example, a request listing all projects `http://127.0.0.1:8000/v1/projects/` can add
a limit and an offset parameter to the number of projects you want to display (running much faster then), example for a limit of 10
projects: `http://127.0.0.1:8000/v1/projects/?limit=10`.
The response will contain the full count of the listing, the link to the previous pagination
request and the link for the next one following the limit and offset you gave, example for `http://127.0.0.1:8000/v1/projects/?limit=10&offset=20` :

```json
{
    "count": 1261,
    "next": "http://127.0.0.1:8000/v1/projects/?limit=10&offset=30",
    "previous": "http://127.0.0.1:8000/v1/projects/?limit=10&offset=10",
    "results": [ ... ]
}
```

## Swagger

The Swagger scheme is automatically generated from the DRF view sets by with use of the library [drf-spectacular](https://drf-spectacular.readthedocs.io/en/latest/).

### Scheme

When the server is running you can download the scheme in json format at route `/api/schema/?format=json`, in development it's usually at http://127.0.0.1:8000/api/schema//?format=json.

### Swagger api documentation

There is two types of documentation available:

- ReDoc at route `/api/schema/redoc`, usually at http://127.0.0.1:8000/api/schema/redoc/
- Swagger UI at route `/api/schema/swagger-ui/`, usually at http://127.0.0.1:8000/api/schema/swagger-ui/

### Generating Postman collection from Swagger scheme

Now that you can have a [Swagger scheme](#scheme), you can import it into Postman as full collection of the rest api ([postman import documentation](https://learning.postman.com/docs/getting-started/importing-and-exporting-data/)).

## Custom commands

### Migrate database

To migrate from old MongoDB you can run the `apps.commons.management.commands.migrate_db` script using

```bash
python manage.py migrate_db
```

### Caveats

- Herited
  from `django-modeltranslation`: [forced to use `get_queryset`](https://django-modeltranslation.readthedocs.io/en/latest/caveats.html#using-in-combination-with-django-rest-framework)
