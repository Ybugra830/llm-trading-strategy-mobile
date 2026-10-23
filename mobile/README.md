# LLM Strategy Lab client

Flutter client for Android, iOS, and Web.

## API configuration

Web builds default to same-origin requests: `/api/v1/strategy-lab/capabilities`
and `/api/v1/strategy-lab/run`. Nginx must proxy `/api/` to the backend without
stripping the prefix. Debug web builds accept an explicit `API_BASE_URL` for
local development. Release web builds ignore it so a release cannot accidentally
target a developer machine. Android emulator defaults to `http://10.0.2.2:8000`;
other native platforms default to `http://127.0.0.1:8000`. Native builds can set
`--dart-define=API_BASE_URL=...`.

## Local web development (PowerShell)

Start the backend from this clone's `backend/` directory in another terminal:

```powershell
$env:CORS_ALLOWED_ORIGINS='["http://127.0.0.1:3005"]'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then from `mobile/`:

```powershell
flutter pub get
flutter run -d web-server --web-hostname 127.0.0.1 --web-port 3005 --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

Open `http://127.0.0.1:3005`. The development server does not proxy `/api/`;
requests go directly to port 8000. If changing the frontend port, update the
backend CORS origin to match and restart the backend. Both terminals must remain
running. Configure `NVIDIA_API_KEY` in this clone's `backend/.env` and start
Docker Desktop before running a real strategy.

The backend assesses strategy intent before generating code. HTTP 422 semantic
errors include `decision`, `reason_code` and Turkish clarification `questions`,
alongside the existing string `detail`. Edit the description to resolve them;
the UI does not automatically retry a rejected/ambiguous prompt. Successful
results optionally include `admission.defaults_applied`, displayed on the result
screen. Prompt length is 1–2000; a short name such as `RSI` requests clarification
instead of becoming an invented strategy. See
[backend admission rules and defaults](../backend/docs/strategy-admission.md).

## Verify and build

```sh
flutter analyze
flutter test
flutter test --platform chrome test/app/core/api/api_config_test.dart
flutter build web --release
```

Deploy only `build/web/` to the web root. Never include backend environment files
or SSH credentials. The Azure demo serves the client from `/var/www/strategy-lab`
and proxies requests to `127.0.0.1:8000`; port 8000 must stay private.
