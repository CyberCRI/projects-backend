# projects-backend

![https://projects.directory.com](https://api.projects.lp-i.org/static/projects_logo.png)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


## Requirements
- Docker Compose V2

## Usage

### Clone the repository

```bash
git clone --recurse-submodules git@github.com:CyberCRI/projects-backend.git 
cd projects-backend
```

### Set up your environment variables

if you want to set your environnement variables (Mostly third-parties secrets):
```bash
cp .env.example .env
```


### Run the stack

```bash
docker compose up
```

The backend and Celery restart multiple times because they keep crashing while Keycloak is not up. After a short moment, your backend will be up and ready.

You can now access: 

- [The Swagger](http://localhost:8000)
- [The backend admin panel](http://localhost:8000/admin)
- [The Keycloak admin panel](http://localhost:8001)

### Execute into the backend container
*The stack need to be running.*
Get a shell access to the backend container
```bash
make bash
```

### Migrate the database
```bash
# inside the container
python manage.py migrate
```

### Collect static files
```bash
# inside the container
python manage.py collectstatic
```

### Compile translations
```bash
# inside the container
python manage.py compilemessages
```

### Default user
A default superadmin is created in keycloak. To import it in Projects, you need to login at least once in the [swagger](http://localhost:8000/api/schema/swagger-ui) or in [Django admin](http://localhost:8000/admin) using these credentials:
- username: `admin` or `admin@localhost.com`
- password: `admin`

You can also use these credentials (use the `admin` username, not the email) to connect to the [Keycloak admin panel](http://localhost/8001)


### Run test

Run all the tests:

```bash
# inside the container
make test
```

Run just one test file or test directory: 

```bash
# inside the container
# ex:path_to_file=apps.accounts.tests.views.test_people_group
python manage.py test <path_to_file> --settings=projects.settings.test 
```

### Continuous Integration

You can check locally that the CI will validate your pull request by running the following commands in your backend container. Your pull request cannot be merged if it doesn't meet these requirements. You can run these tests locally before asking to merge your PR, or you can let the CI run them for you remotely.

1. Respect format rules:

```bash
# inside the container
make format
```

This will automatically update your files

2. Respect lint rules:

```bash
# inside the container
make lint
```

This will return erros that you need to fix manually. If there are some, fix them then repeat step 1.

3. Keep translations up to date:

```bash
# inside the container
make makemessages
```

This will detect changes in translated messages. Even if you didn't add, remove or modify a translated message, this might update some files because they depend on the line of the messages in the code files.

If there are new messages, be sure to add the translation after running this command

4. Create migrations if needed:

```bash
# inside the container
python manage.py makemigrations
```

5. Be sure that all tests pass

```bash
# inside the container
make test
```