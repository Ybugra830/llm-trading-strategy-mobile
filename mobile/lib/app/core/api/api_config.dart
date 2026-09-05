import 'package:flutter/foundation.dart';

class ApiConfig {
  ApiConfig({String? baseUrl})
    : baseUrl = _normalize(baseUrl ?? resolvedBaseUrl);

  static const _definedBaseUrl = String.fromEnvironment('API_BASE_URL');

  static String get resolvedBaseUrl {
    // Web requests use the hosting origin and Nginx's /api/ proxy.
    if (kIsWeb) return '';
    if (_definedBaseUrl.trim().isNotEmpty) return _definedBaseUrl;

    return defaultTargetPlatform == TargetPlatform.android
        ? 'http://10.0.2.2:8000'
        : 'http://127.0.0.1:8000';
  }

  final String baseUrl;

  static const capabilitiesTimeout = Duration(seconds: 15);
  static const runTimeout = Duration(minutes: 5);

  static String _normalize(String value) {
    final trimmed = value.trim();
    return trimmed.endsWith('/')
        ? trimmed.substring(0, trimmed.length - 1)
        : trimmed;
  }
}
