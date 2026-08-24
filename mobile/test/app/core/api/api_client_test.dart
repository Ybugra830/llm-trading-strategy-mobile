import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:llm_trading_strategy_mobile/app/core/api/api_client.dart';
import 'package:llm_trading_strategy_mobile/app/core/api/api_config.dart';
import 'package:llm_trading_strategy_mobile/app/core/api/api_exception.dart';

import '../../../helpers/api_fixtures.dart';

void main() {
  test('returns a JSON object for successful response', () async {
    final dio = Dio();
    dio.httpClientAdapter = StubHttpClientAdapter(
      (_) async => ResponseBody.fromString(
        jsonEncode({'ok': true}),
        200,
        headers: {
          Headers.contentTypeHeader: [Headers.jsonContentType],
        },
      ),
    );
    final client = ApiClient(
      config: ApiConfig(baseUrl: 'http://test'),
      dio: dio,
    );

    expect(
      await client.getObject('/value', timeout: const Duration(seconds: 1)),
      {'ok': true},
    );
  });

  test('keeps only safe string detail on HTTP error', () async {
    final dio = Dio();
    dio.httpClientAdapter = StubHttpClientAdapter(
      (_) async => ResponseBody.fromString(
        jsonEncode({'detail': 'Safe message'}),
        422,
        headers: {
          Headers.contentTypeHeader: [Headers.jsonContentType],
        },
      ),
    );
    final client = ApiClient(
      config: ApiConfig(baseUrl: 'http://test'),
      dio: dio,
    );

    await expectLater(
      client.getObject('/value', timeout: const Duration(seconds: 1)),
      throwsA(
        isA<ApiException>()
            .having((error) => error.statusCode, 'status', 422)
            .having((error) => error.safeDetail, 'detail', 'Safe message'),
      ),
    );
  });
}
