import 'package:dio/dio.dart';

import '../../../core/api/api_client.dart';
import '../../../core/api/api_config.dart';
import '../../../core/api/api_exception.dart';
import '../models/capabilities_response.dart';
import '../models/strategy_run_request.dart';
import '../models/strategy_run_response.dart';

class StrategyLabApi {
  const StrategyLabApi(this._client);

  final ApiClient _client;

  Future<CapabilitiesResponse> getCapabilities() async {
    final json = await _client.getObject(
      '/api/v1/strategy-lab/capabilities',
      timeout: ApiConfig.capabilitiesTimeout,
    );
    try {
      return CapabilitiesResponse.fromJson(json);
    } on Object {
      throw const ApiException(ApiExceptionKind.invalidResponse);
    }
  }

  Future<StrategyRunResponse> run(
    StrategyRunRequest request, {
    CancelToken? cancelToken,
  }) async {
    final json = await _client.postObject(
      '/api/v1/strategy-lab/run',
      body: request.toJson(),
      timeout: ApiConfig.runTimeout,
      cancelToken: cancelToken,
    );
    try {
      return StrategyRunResponse.fromJson(json);
    } on Object {
      throw const ApiException(ApiExceptionKind.invalidResponse);
    }
  }
}
