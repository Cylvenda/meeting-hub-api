# Secure Meeting API

A Django and Django REST Framework backend for a Virtual Private Meeting Platform. The project currently includes custom email-based authentication, cookie-backed JWT login flows, group management, meeting workflows, and in-app notifications.

## Current Scope

Implemented areas:

- Custom user model with email login
- Djoser authentication endpoints
- Cookie-based JWT login, refresh, logout, and current-user endpoints
- Group creation, membership management, and invitation flows
- Meeting CRUD with start, end, join, leave, attendance, and minutes endpoints
- Notification listing and mark-as-read endpoints
- OpenAPI schema generation with Swagger UI
- Django admin support

Known gaps:

- Automated tests are still placeholders
- Email activation depends on SMTP environment configuration
- Settings are still development-oriented

## Tech Stack

- Python
- Django 6
- Django REST Framework
- Djoser
- SimpleJWT
- drf-spectacular
- django-cors-headers
- SQLite for local development

## Project Structure

```text
backend/
|-- manage.py
|-- requirements.txt
|-- README.md
|-- config/                  # Django project settings and root routing
|-- apps/
|   |-- accounts/            # Custom user model and authentication flows
|   |-- groups/              # Groups, memberships, and invitations
|   |-- meetings/            # Meetings, agenda items, attendance, minutes
|   |-- notifications/       # User notifications
|-- templates/
|   |-- email/               # Activation email template(s)
|-- venv/                    # Local virtual environment if created locally
```

## Installation

1. Create and activate a virtual environment.

```bash
python -m venv venv
source venv/bin/activate
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Apply migrations.

```bash
python manage.py migrate
```

4. Create a superuser if needed.

```bash
python manage.py createsuperuser
```

5. Run the development server.

```bash
python manage.py runserver 0.0.0.0:8000
```

For LAN testing, find your machine IP with:

```bash
ip a
```

Then open `http://<your-local-ip>:8000` from another device on the same network.

## Environment Notes

The project loads variables from a local `.env` file if present.

Relevant settings include:

- `EMAIL_BACKEND`
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_USE_TLS`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `DEFAULT_FROM_EMAIL`
- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `LIVEKIT_TOKEN_TTL_MINUTES`
- `ALLOWED_HOSTS`
- `DEV_ALLOW_ALL_HOSTS`
- `CORS_ALLOWED_ORIGINS`
- `CSRF_TRUSTED_ORIGINS`

If these are not configured, Djoser activation emails will not work end-to-end.
If the LiveKit variables are not configured, meeting join requests will return a
service-unavailable response instead of a connection token.

For development on a shared Wi-Fi or LAN:

- `DEV_ALLOW_ALL_HOSTS=True` lets Django accept requests from changing local IPs.
- If your frontend talks to Django directly from another origin, add that origin to
  `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`.

## Authentication

### Djoser endpoints

Mounted under:

- `/api/auth/`

Examples include:

- `POST /api/auth/users/`
- `POST /api/auth/jwt/create/`
- `POST /api/auth/jwt/refresh/`
- `POST /api/auth/users/activation/`

### Cookie-based auth endpoints

Mounted under:

- `/api/me/auth/login/`
- `/api/me/auth/refresh/`
- `/api/me/auth/verify/`
- `/api/me/auth/logout/`
- `/api/me/auth/csrf/`
- `/api/me/auth/me/`

The project uses a custom cookie JWT flow in the `accounts` app, with cookies named:

- `access`
- `refresh`

Notes:

- `/api/me/auth/refresh/` is the primary refresh endpoint
- `/api/me/auth/csrf/` is still available as a backward-compatible alias
- `/api/me/auth/verify/` verifies the current access token

## API Surface

### Documentation

- `GET /` - Swagger UI
- `GET /api/schema/` - OpenAPI schema

### Groups

Base path:

- `/api/groups/`

Available routes include:

- `GET /api/groups/`
- `POST /api/groups/`
- `GET /api/groups/<uuid>/`
- `GET /api/groups/<uuid>/members/`
- `POST /api/groups/<group_uuid>/members/add/`
- `PATCH /api/groups/<group_uuid>/members/<membership_uuid>/verify/`
- `PATCH /api/groups/<group_uuid>/members/<membership_uuid>/activate/`
- `POST /api/groups/<group_uuid>/invitations/send/`
- `GET /api/groups/<group_uuid>/invitations/`
- `GET /api/groups/invitations/my/`
- `POST /api/groups/invitations/<invitation_uuid>/respond/`
- `POST /api/groups/<group_uuid>/invitations/<invitation_uuid>/cancel/`

### Meetings

Base path:

- `/api/meetings/`
- `/api/agenda-items/`

Router-backed endpoints include standard CRUD operations plus custom meeting actions:

- `POST /api/meetings/<id>/start/`
- `POST /api/meetings/<id>/end/`
- `POST /api/meetings/<id>/join/`
- `POST /api/meetings/<id>/leave/`
- `GET /api/meetings/<id>/participants/`
- `GET /api/meetings/<id>/attendance/`
- `GET /api/meetings/<id>/minutes/`
- `POST /api/meetings/<id>/minutes/`
- `PATCH /api/meetings/<id>/minutes/`

### Notifications

Base path:

- `/api/notifications/`

Routes:

- `GET /api/notifications/`
- `PATCH /api/notifications/<notification_uuid>/read/`

## Running Checks

Basic Django project validation:

```bash
python manage.py check
```

Run tests:

```bash
python manage.py test
```

Note: test modules exist, but they are currently scaffold-level and do not provide meaningful coverage yet.

## Development Status

Current development assumptions:

- SQLite is used locally through `db.sqlite3`
- CSRF and auth cookie settings are configured for local development
- Trusted frontend origins currently target local Vite defaults

Before production use, review at minimum:

- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- auth cookie security flags
- CSRF trusted origins
- database configuration
- frontend domain and CORS environment variables
- email backend configuration

## License

This project is licensed under the MIT License.
