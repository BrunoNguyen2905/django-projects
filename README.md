# Lithium: A Django-Powered Boilerplate

Lithium is a batteries-included Django starter project with everything you need to start coding, including user authentication, static files, default styling, debugging, DRY forms, custom error pages, and more.

> This project was formerly known as _DjangoX_ but was renamed to _Lithium_ in November 2024.

https://github.com/user-attachments/assets/8698e9dd-1794-4f96-9c3f-85add17e330b

## 👋 Free Newsletter

[Sign up for updates](https://buttondown.com/lithiumsaas) to the free and upcoming premium SaaS version!

## 🚀 Features

- Django 5.1 & Python 3.13
- Installation via [uv](https://github.com/astral-sh/uv), [Pip](https://pypi.org/project/pip/) or [Docker](https://www.docker.com/)
- User authentication--log in, sign up, password reset--via [django-allauth](https://github.com/pennersr/django-allauth)
- Static files configured with [Whitenoise](http://whitenoise.evans.io/en/stable/index.html)
- Styling with [Bootstrap v5](https://getbootstrap.com/)
- Debugging with [django-debug-toolbar](https://github.com/jazzband/django-debug-toolbar)
- DRY forms with [django-crispy-forms](https://github.com/django-crispy-forms/django-crispy-forms)
- Custom 404, 500, and 403 error pages

## Table of Contents

- **[Installation](#installation)**
  - [uv](#uv)
  - [Pip](#pip)
  - [Docker](#docker)
- [Next Steps](#next-steps)
- [Contributing](#contributing)
- [Support](#support)
- [License](#license)

## 📖 Installation

Lithium can be installed via Pip or Docker. To start, clone the repo to your local computer and change into the proper directory.

```
$ git clone https://github.com/wsvincent/lithium.git
$ cd lithium
```

### uv

You can use [uv](https://docs.astral.sh/uv/) to create a dedicated virtual environment.

```
$ uv sync
```

When you add or remove packages with `uv add` or `uv remove`, regenerate `requirements.txt` so Pip and Docker users get the same dependencies:

```
$ uv export --format requirements.txt --no-dev --no-emit-project --no-hashes -o requirements.txt
```

Then run `migrate` to configure the initial database. The command `createsuperuser` will create a new superuser account for accessing the admin. Execute the `runserver` command to start up the local server.

```
$ uv run manage.py migrate
$ uv run manage.py createsuperuser
$ uv run manage.py runserver
# Load the site at http://127.0.0.1:8000 or http://127.0.0.1:8000/admin for the admin
```

### Pip

To use Pip, create a new virtual environment and then install all packages hosted in `requirements.txt`. Run `migrate` to configure the initial database. and `createsuperuser` to create a new superuser account for accessing the admin. Execute the `runserver` command to start up the local server.

```
(.venv) $ pip install -r requirements.txt
(.venv) $ python manage.py migrate
(.venv) $ python manage.py createsuperuser
(.venv) $ python manage.py runserver
# Load the site at http://127.0.0.1:8000 or http://127.0.0.1:8000/admin for the admin
```

### Docker

To use Docker with PostgreSQL as the database update the `DATABASES` section of `django_project/settings.py` to reflect the following:

```python
# django_project/settings.py
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "postgres",
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": "db",  # set in docker-compose.yml
        "PORT": 5432,  # default postgres port
    }
}
```

The `INTERNAL_IPS` configuration in `django_project/settings.py` must be also be updated:

```python
# config/settings.py
# django-debug-toolbar
import socket
hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
INTERNAL_IPS = [ip[:-1] + "1" for ip in ips]
```

And then proceed to build the Docker image, run the container, and execute the standard commands within Docker.

```
$ docker compose up -d --build
$ docker compose exec web python manage.py migrate
$ docker compose exec web python manage.py createsuperuser
# Load the site at http://127.0.0.1:8000 or http://127.0.0.1:8000/admin for the admin
```

## Next Steps

- **Create a new Django app**: Use `uv run python manage.py startapp <app_name>` to create a new app (e.g., `uv run python manage.py startapp blog`). Then add the new app to `INSTALLED_APPS` in `django_project/settings.py`.
- **Test the music search flow**: Run `uv run python verify_search_flow.py "uplifting cinematic piano build"` to test the complete LLM → taxonomy selection → Soundstripe API flow. Use `--dry-run` to test only LLM taxonomy generation without API calls.

### Testing the search API from bash

From the project root, in a terminal:

```bash
# 1. Ensure .env has OPENAI_API_KEY and SOUNDSTRIPE_API_KEY_DEVELOPMENT
cd /path/to/lithium

# 2. Full flow (LLM + Soundstripe, 3 rounds max, 1 API call per round)
uv run python verify_search_flow.py "acoustic beautiful chill lofi"

# 3. Dry run (LLM only, no Soundstripe calls)
uv run python verify_search_flow.py "uplifting cinematic piano" --dry-run

# 4. Quick Soundstripe connectivity check (no LLM)
uv run python test_soundstripe_api.py
```

To call the Soundstripe API directly with curl (replace `YOUR_API_KEY` with the value from `.env`):

```bash
# List songs with a text query and optional tag filters
curl -s -H "Authorization: Token YOUR_API_KEY" \
  -H "Accept: application/vnd.api+json" \
  "https://api.soundstripe.com/v1/songs?filter[q]=chill&filter[tags][genre]=Lo-Fi&filter[tags][mood]=Chill&page[size]=5" | jq .
```
- Add environment variables. There are multiple packages but I personally prefer [environs](https://pypi.org/project/environs/).
- Add [gunicorn](https://pypi.org/project/gunicorn/) as the production web server.
- Update the [EMAIL_BACKEND](https://docs.djangoproject.com/en/4.0/topics/email/#module-django.core.mail) and connect with a mail provider.
- Make the [admin more secure](https://opensource.com/article/18/1/10-tips-making-django-admin-more-secure).
- `django-allauth` supports [social authentication](https://django-allauth.readthedocs.io/en/latest/socialaccount/index.html) if you need that.

I cover all of these steps in tutorials and premium courses over at [LearnDjango.com](https://learndjango.com).

## 🤝 Contributing

Contributions, issues and feature requests are welcome! See [CONTRIBUTING.md](https://github.com/wsvincent/lithium/blob/master/CONTRIBUTING.md).

## ⭐️ Support

Give a ⭐️ if this project helped you!

## License

[The MIT License](LICENSE)
