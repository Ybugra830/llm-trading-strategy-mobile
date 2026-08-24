import 'package:dio/dio.dart';

import '../../../core/api/api_exception.dart';
import '../models/capabilities_response.dart';
import '../models/strategy_lab_failure.dart';
import '../models/strategy_run_request.dart';
import '../models/strategy_run_response.dart';
import 'strategy_lab_api.dart';

abstract interface class StrategyLabRepository {
  Future<CapabilitiesResponse> getCapabilities();

  Future<StrategyRunResponse> run(
    StrategyRunRequest request, {
    CancelToken? cancelToken,
  });
}

class HttpStrategyLabRepository implements StrategyLabRepository {
  const HttpStrategyLabRepository(this._api);

  final StrategyLabApi _api;

  @override
  Future<CapabilitiesResponse> getCapabilities() async {
    try {
      final response = await _api.getCapabilities();
      if (response.supportedSymbols.isEmpty ||
          response.prompt.minLength < 1 ||
          response.prompt.maxLength < response.prompt.minLength) {
        throw const StrategyLabException(
          StrategyLabFailure(
            type: StrategyLabFailureType.unknown,
            message: 'Backend capabilities are incomplete.',
          ),
        );
      }
      return response;
    } on StrategyLabException {
      rethrow;
    } on ApiException catch (error) {
      throw StrategyLabException(_mapApiError(error));
    } on Object {
      throw const StrategyLabException(
        StrategyLabFailure(
          type: StrategyLabFailureType.unknown,
          message: 'The server returned an unexpected response.',
        ),
      );
    }
  }

  @override
  Future<StrategyRunResponse> run(
    StrategyRunRequest request, {
    CancelToken? cancelToken,
  }) async {
    try {
      return await _api.run(request, cancelToken: cancelToken);
    } on ApiException catch (error) {
      throw StrategyLabException(_mapApiError(error));
    } on Object {
      throw const StrategyLabException(
        StrategyLabFailure(
          type: StrategyLabFailureType.unknown,
          message: 'The server returned an unexpected response.',
        ),
      );
    }
  }

  static StrategyLabFailure _mapApiError(ApiException error) {
    if (error.kind == ApiExceptionKind.cancelled) {
      return const StrategyLabFailure(
        type: StrategyLabFailureType.cancelled,
        message: 'Request cancelled.',
      );
    }
    if (error.kind == ApiExceptionKind.network ||
        error.kind == ApiExceptionKind.timeout) {
      return const StrategyLabFailure(
        type: StrategyLabFailureType.network,
        message:
            'Could not reach the Strategy Lab service. Check your connection and try again.',
      );
    }
    if (error.kind == ApiExceptionKind.invalidResponse) {
      return const StrategyLabFailure(
        type: StrategyLabFailureType.unknown,
        message: 'The server returned an unexpected response.',
      );
    }

    final detail = error.safeDetail;
    switch (error.statusCode) {
      case 422:
        return StrategyLabFailure(
          type: StrategyLabFailureType.validation,
          message: detail ?? 'Check the strategy inputs and try again.',
        );
      case 502:
        return StrategyLabFailure(
          type: StrategyLabFailureType.provider,
          message:
              detail ??
              'Strategy generation or market data is temporarily unavailable.',
        );
      case 503:
        return StrategyLabFailure(
          type: StrategyLabFailureType.sandbox,
          message:
              detail ??
              'The secure strategy runtime is temporarily unavailable.',
        );
      case 500:
        return const StrategyLabFailure(
          type: StrategyLabFailureType.backend,
          message: 'Strategy Lab could not complete the request right now.',
        );
      default:
        return const StrategyLabFailure(
          type: StrategyLabFailureType.unknown,
          message: 'Something went wrong. Please try again later.',
        );
    }
  }
}
