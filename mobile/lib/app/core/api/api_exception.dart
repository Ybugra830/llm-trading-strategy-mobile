enum ApiExceptionKind { http, network, timeout, cancelled, invalidResponse }

class ApiException implements Exception {
  const ApiException(
    this.kind, {
    this.statusCode,
    this.safeDetail,
    this.decision,
    this.reasonCode,
    this.questions = const [],
  });

  final ApiExceptionKind kind;
  final int? statusCode;
  final String? safeDetail;
  final String? decision;
  final String? reasonCode;
  final List<String> questions;
}
