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
