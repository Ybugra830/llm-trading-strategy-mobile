import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:llm_trading_strategy_mobile/app/core/api/api_config.dart';

void main() {
  tearDown(() => debugDefaultTargetPlatformOverride = null);

  test('web stays same-origin and Android retains its emulator address', () {
    debugDefaultTargetPlatformOverride = TargetPlatform.android;
    expect(ApiConfig().baseUrl, kIsWeb ? '' : 'http://10.0.2.2:8000');
  });

  test('web stays same-origin and other native platforms use localhost', () {
    debugDefaultTargetPlatformOverride = TargetPlatform.iOS;
    expect(ApiConfig().baseUrl, kIsWeb ? '' : 'http://127.0.0.1:8000');
  });

  test('same-origin requests preserve the full API prefix', () {
    for (final endpoint in ['capabilities', 'run']) {
      final path = '/api/v1/strategy-lab/$endpoint';
      final options = RequestOptions(
        baseUrl: ApiConfig(baseUrl: '').baseUrl,
        path: path,
      );
      expect(options.uri.toString(), path);
    }
  });

  test('explicit test configuration normalizes its trailing slash', () {
    expect(ApiConfig(baseUrl: ' http://test/ ').baseUrl, 'http://test');
  });
}
