# LLM Strategy Lab client

Flutter client for Android, iOS, and Web.

## API configuration

Web builds use same-origin requests: `/api/v1/strategy-lab/capabilities` and
`/api/v1/strategy-lab/run`. Nginx must proxy `/api/` to the backend without
stripping the prefix. Web ignores `API_BASE_URL` so a release cannot accidentally
target a developer machine. Android emulator defaults to `http://10.0.2.2:8000`;
other native platforms default to `http://127.0.0.1:8000`. Native builds can set
`--dart-define=API_BASE_URL=...`.

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
