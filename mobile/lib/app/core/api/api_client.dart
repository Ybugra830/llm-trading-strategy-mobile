import 'package:dio/dio.dart';

import 'api_config.dart';
import 'api_exception.dart';

class ApiClient {
  ApiClient({required ApiConfig config, Dio? dio}) : _dio = dio ?? Dio() {
    _dio.options = _dio.options.copyWith(
      baseUrl: config.baseUrl,
      connectTimeout: const Duration(seconds: 10),
      sendTimeout: const Duration(seconds: 15),
      responseType: ResponseType.json,
      headers: const {'Accept': 'application/json'},
      validateStatus: (_) => true,
    );
  }

  final Dio _dio;

  Future<Map<String, dynamic>> getObject(
    String path, {
    required Duration timeout,
  }) async {
    return _request(
      () => _dio.get<Object?>(path, options: Options(receiveTimeout: timeout)),
    );
  }

  Future<Map<String, dynamic>> postObject(
    String path, {
    required Map<String, dynamic> body,
    required Duration timeout,
    CancelToken? cancelToken,
  }) async {
    return _request(
      () => _dio.post<Object?>(
        path,
        data: body,
        cancelToken: cancelToken,
        options: Options(
          receiveTimeout: timeout,
          sendTimeout: const Duration(seconds: 15),
          contentType: Headers.jsonContentType,
        ),
      ),
    );
  }

  Future<Map<String, dynamic>> _request(
    Future<Response<Object?>> Function() send,
  ) async {
    try {
      final response = await send();
      final statusCode = response.statusCode ?? 0;
      if (statusCode < 200 || statusCode >= 300) {
        throw ApiException(
          ApiExceptionKind.http,
          statusCode: statusCode,
          safeDetail: _extractSafeDetail(response.data),
        );
      }
      final data = response.data;
      if (data is! Map) {
        throw const ApiException(ApiExceptionKind.invalidResponse);
      }
      return Map<String, dynamic>.from(data);
    } on ApiException {
      rethrow;
    } on DioException catch (error) {
      if (CancelToken.isCancel(error)) {
        throw const ApiException(ApiExceptionKind.cancelled);
      }
      if (error.type == DioExceptionType.connectionTimeout ||
          error.type == DioExceptionType.sendTimeout ||
          error.type == DioExceptionType.receiveTimeout) {
        throw const ApiException(ApiExceptionKind.timeout);
      }
      if (error.type == DioExceptionType.badResponse) {
        throw ApiException(
          ApiExceptionKind.http,
          statusCode: error.response?.statusCode,
          safeDetail: _extractSafeDetail(error.response?.data),
        );
      }
      throw const ApiException(ApiExceptionKind.network);
    } on FormatException {
      throw const ApiException(ApiExceptionKind.invalidResponse);
    }
  }

  static String? _extractSafeDetail(Object? body) {
    if (body is Map && body['detail'] is String) {
      final detail = (body['detail'] as String).trim();
      if (detail.isNotEmpty && detail.length <= 300) return detail;
    }
    return null;
  }
}
