enum ApiExceptionKind { http, network, timeout, cancelled, invalidResponse }

class ApiException implements Exception {
  const ApiException(this.kind, {this.statusCode, this.safeDetail});

  final ApiExceptionKind kind;
  final int? statusCode;
  final String? safeDetail;
}
