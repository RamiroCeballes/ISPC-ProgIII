# Django Backend API

Backend de autenticación con Django REST Framework, JWT y OAuth2 social (Google/GitHub), más chat y notificaciones en tiempo real con Django Channels y WebSockets.

## Estado Actual

- JWT con `access` y `refresh`
- Registro de usuarios con validación de username y email únicos
- Login / logout con blacklist de refresh tokens
- Recuperación de contraseña por OTP (3 pasos)
- OAuth2 social con django-allauth
- Endpoint puente para frontend SPA: `/api/oauth/success/`
- CORS habilitado para frontend Angular
- Chat por salas en tiempo real vía WebSocket (Django Channels)
- Notificaciones push en tiempo real por WebSocket, disparables desde cualquier parte del backend

## Requisitos

- Python 3.13+
- Entorno virtual

## Setup Rápido

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

### macOS/Linux

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Servidor: `http://localhost:8000`

`python manage.py runserver` ahora levanta un servidor **ASGI/Daphne** (verás
`Starting ASGI/Daphne version ... development server` en la consola), capaz de
atender HTTP y WebSockets al mismo tiempo.

### Redis (channel layer)

El chat y las notificaciones usan Redis como *channel layer* para repartir
mensajes entre consumers. Levantarlo con Docker:

```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

Si no tenés Redis a mano, poné `USE_REDIS_CHANNEL_LAYER=False` en tu `.env`
para usar el backend en memoria (solo sirve para desarrollo en un único
proceso, nunca en producción).

## Docker

Todo el stack (Django ASGI + PostgreSQL + Redis) se levanta con un comando:

```bash
cp .env.example .env     # completar SECRET_KEY y credenciales OAuth
docker compose up --build
```

Servidor en `http://localhost:8000`. El `entrypoint` espera a PostgreSQL,
aplica las migraciones y arranca **daphne** (no gunicorn: gunicorn es WSGI y no
sostiene los WebSockets de Channels).

Comandos útiles:

```bash
docker compose logs -f backend                        # seguir los logs
docker compose exec backend python manage.py test     # correr los tests
docker compose exec backend python manage.py createsuperuser
docker compose down -v                                # borrar también la base
```

### Health checks

| Endpoint | Uso |
|---|---|
| `GET /health/` | Liveness. No toca la base ni Redis: es el que debe usar el load balancer. |
| `GET /health/ready/` | Readiness. Devuelve 503 si PostgreSQL o Redis no responden. |

El health check del balanceador debe apuntar a `/health/`: si apuntara a
`/health/ready/`, una caída momentánea de la base daría de baja tareas que en
realidad están sanas.

### Base de datos

`settings.py` elige el motor según el entorno: si `DB_HOST` está definido usa
PostgreSQL (el contenedor en local, RDS en producción); si está vacío, SQLite.
Así los tests y el desarrollo suelto siguen andando sin levantar nada.

## Despliegue en AWS ECR

```bash
# credenciales de AWS configuradas previamente (aws configure / aws sso login)
export AWS_REGION=us-east-1
export ECR_REPOSITORY=ispc-progiii-backend

./deploy/ecr-push.sh            # tag = SHA corto de git
./deploy/ecr-push.sh v1.0.0     # tag explícito
```

El script crea el repositorio en ECR si no existe, se autentica, construye y
publica la imagen con el tag pedido y con `latest`.

> **Arquitectura:** el script construye para `linux/amd64`. En una Mac con
> Apple Silicon el build por defecto sale `arm64` y la tarea de ECS muere con
> `exec format error`. Si el servicio se creó con `runtimePlatform` ARM64,
> exportar `PLATFORM=linux/arm64`.

### Variables en producción

La imagen **no** incluye el `.env` (está en `.dockerignore`): los valores se
inyectan desde la task definition de ECS, Secrets Manager o SSM Parameter
Store. Las mínimas para que arranque sana:

| Variable | Valor típico en producción |
|---|---|
| `SECRET_KEY` | una clave larga y aleatoria, nunca la de desarrollo |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | el dominio público de la API |
| `CSRF_TRUSTED_ORIGINS` | `https://api.midominio.com` |
| `SECURE_SSL` | `True` (activa HSTS y cookies seguras) |
| `USE_X_FORWARDED_PROTO` | `True` si hay un ALB terminando TLS |
| `DB_HOST` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | endpoint de RDS |
| `REDIS_HOST` / `REDIS_PORT` | endpoint de ElastiCache |
| `FIELD_ENCRYPTION_KEY` | clave propia; si cambia, los datos ya cifrados no se leen más |
| `RUN_MIGRATIONS` | `False` con más de una réplica (migrar como tarea aparte) |

Con `SECURE_SSL=True` y una `SECRET_KEY` propia, `manage.py check --deploy` no
reporta ningún problema.

> **WebSockets detrás de un ALB:** hay que subir el *idle timeout* del target
> group (por defecto 60 s corta las conexiones de chat) y mantener *sticky
> sessions* apagadas — el reparto entre réplicas lo hace el channel layer de
> Redis, no el balanceador.

## Variables de Entorno Clave

- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `CORS_ALLOWED_ORIGINS`
- `FRONTEND_URL`
- `GOOGLE_OAUTH2_KEY`
- `GOOGLE_OAUTH2_SECRET`
- `GITHUB_APP_ID`
- `GITHUB_SECRET`
- `USE_REDIS_CHANNEL_LAYER` / `REDIS_HOST` / `REDIS_PORT`
- `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` (PostgreSQL; vacío = SQLite)
- `SECURE_SSL` / `USE_X_FORWARDED_PROTO` / `CSRF_TRUSTED_ORIGINS` (producción con HTTPS)
- `FIELD_ENCRYPTION_KEY` / `RUN_MIGRATIONS`

## Endpoints Principales

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/api/register/` | Registro (retorna `access` + `refresh`) |
| POST | `/api/login/` | Login JWT |
| POST | `/api/logout/` | Logout + blacklist |
| GET | `/api/user/` | Perfil del usuario autenticado |
| PUT | `/api/user/change-password/` | Cambio de contraseña |
| POST | `/api/token/refresh/` | Nuevo access token |
| POST | `/api/password-reset-request/` | Solicitar OTP |
| POST | `/api/password-reset-verify-otp/` | Verificar OTP |
| POST | `/api/password-reset-confirm/` | Confirmar reset |
| GET | `/accounts/google/login/?process=login` | Inicio OAuth Google |
| GET | `/accounts/github/login/?process=login` | Inicio OAuth GitHub |

## Chat en tiempo real (WebSocket)

| Protocolo | Endpoint | Descripción |
|---|---|---|
| WS | `ws://localhost:8000/ws/chat/<room_slug>/?token=<access>` | Conectarse a una sala (se crea sola si no existe) |
| GET | `/api/chat/rooms/` | Listar salas existentes |
| GET | `/api/chat/rooms/<room_slug>/history/` | Últimos 50 mensajes de la sala |

Mensajes que se envían por el socket:

```jsonc
{ "type": "chat.message", "text": "hola a todos" }
{ "type": "chat.typing" }
```

Eventos que llegan por el socket: `chat.message`, `chat.presence` (`join`/`leave`), `chat.typing`, `error`.

Si un mensaje contiene `@usuario`, se dispara automáticamente una notificación en tiempo real para ese usuario (ver `chat/signals.py`).

## Notificaciones en tiempo real (WebSocket)

| Protocolo/Método | Endpoint | Descripción |
|---|---|---|
| WS | `ws://localhost:8000/ws/notifications/?token=<access>` | Suscribirse a las notificaciones propias |
| GET | `/api/notifications/` | Listar notificaciones (paginado) |
| GET | `/api/notifications/?unread=1` | Solo las no leídas |
| GET | `/api/notifications/unread-count/` | Contador de no leídas |
| POST | `/api/notifications/<id>/read/` | Marcar una como leída |
| POST | `/api/notifications/mark-all-read/` | Marcar todas como leídas |

Al conectarse, el socket manda `{"type": "notification.unread", "count": N}`; cada notificación nueva llega como `{"type": "notification.new", "notification": {...}}`. Cualquier parte del backend puede disparar una notificación con:

```python
from notifications.services import notify
notify(user, title="Nuevo ticket asignado", body="...", link="/tickets/42")
```

### Autenticación de los WebSockets

La API `WebSocket` del navegador no permite mandar cabeceras `Authorization`,
así que el access token JWT se manda como query string
(`?token=<access_token>`). Lo resuelve `backend/ws_auth_middleware.py`. Un
socket sin token válido se cierra con el código propio `4001`.

## OAuth en Producción

1. Configurar credenciales OAuth en `.env`.
2. Registrar callbacks en proveedores:
   - `http://localhost:8000/accounts/google/login/callback/`
   - `http://localhost:8000/accounts/github/login/callback/`
3. Verificar `FRONTEND_URL` correcto para redirección al frontend.

## Testing

```bash
python manage.py check
python manage.py test accounts
python manage.py test chat notifications
```

Actualmente la suite `accounts` ejecuta 30 tests; `chat` y `notifications` prueban el flujo completo de WebSocket (conectar, autenticar por JWT, enviar/recibir, persistencia) con `channels.testing.WebsocketCommunicator` sobre un channel layer en memoria.

## Documentación Completa

Ver `DOCUMENTATION.md` para guía detallada de JWT, OAuth2, OTP, troubleshooting y verificación end-to-end.
