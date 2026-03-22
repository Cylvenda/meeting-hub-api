# Secure Meeting API

A secure backend for a virtual meeting system built with Django and Django REST Framework. The project is structured for authentication-first development, with custom user management already in place and dedicated apps for meetings and notifications ready to grow into a full private meeting platform.

## Features

### Available now

- JWT authentication with email login
- Custom user model
- Djoser-powered authentication endpoints
- OpenAPI schema generation with Swagger UI
- Django admin support

### In progress / planned

- Meeting creation and management
- Invitation workflows
- Attendance tracking
- Role-based access control
- Activity monitoring and reporting

## Tech Stack

- Backend: Django, Django REST Framework
- Authentication: Djoser, SimpleJWT
- API docs: drf-spectacular
- Database: SQLite for development

## Project Structure

```text
meet-back/
|-- manage.py
|-- requirements.txt
|-- config/              # Project settings, URLs, ASGI/WSGI
|-- apps/
|   |-- accounts/        # Custom user model and auth-related app
|   |-- meetings/        # Meeting domain app
|   |-- notifications/   # Notification domain app
|-- db.sqlite3           # Local development database
|-- static/
|-- media/
|-- templates/
```

## Installation

### 1. Clone the project

```bash
git clone <your-repository-url>
cd meet-back
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

For Windows:

```bash
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Apply migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create a superuser

```bash
python manage.py createsuperuser
```

### 6. Run the development server

```bash
python manage.py runserver
```

## Authentication Setup

This project uses a custom user model with:

- `email` as the login field
- `username`
- `phone`
- `first_name`
- `last_name`

Djoser is configured to authenticate users by email, and SimpleJWT is used for token-based auth.

Current authentication-related settings include:

```python
AUTH_USER_MODEL = "accounts.User"

DJOSER = {
    "LOGIN_FIELD": "email",
    "SEND_ACTIVATION_EMAIL": True,
}

SIMPLE_JWT = {
    "AUTH_HEADER_TYPES": ("JWT",),
}
```

## API Endpoints

### Authentication

- `POST /auth/users/` - register a user
- `POST /auth/jwt/create/` - obtain JWT tokens
- `POST /auth/jwt/refresh/` - refresh an access token
- `GET /auth/users/me/` - get the current authenticated user
- `POST /auth/users/activation/` - activate an account

### API documentation

- `GET /api/schema/` - OpenAPI schema
- `GET /` - Swagger UI

## Current Notes

- The project currently uses SQLite in development through `db.sqlite3`.
- The `meetings` and `notifications` apps exist, but their domain models and API views are still scaffold-level at the moment.
- Email activation is enabled in Djoser, so email backend settings will need to be configured before activation flows work end-to-end.

## Roadmap

- Build meeting CRUD endpoints
- Add invitation and participant workflows
- Implement role-based permissions
- Add attendance history and reporting
- Configure PostgreSQL for production deployments

## Author

Cylvenda

## License

This project is licensed under the MIT License.
