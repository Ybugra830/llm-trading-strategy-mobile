import 'dart:async';

import 'package:dio/dio.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/data/strategy_lab_repository.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/capabilities_response.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/strategy_run_request.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/strategy_run_response.dart';

class FakeStrategyLabRepository implements StrategyLabRepository {
  FakeStrategyLabRepository({
    required this.capabilitiesResult,
    this.runResult,
    this.capabilitiesError,
    this.runError,
    this.pendingRun,
  });

  CapabilitiesResponse capabilitiesResult;
  StrategyRunResponse? runResult;
  Object? capabilitiesError;
  Object? runError;
  Completer<StrategyRunResponse>? pendingRun;
  int capabilitiesCalls = 0;
  int runCalls = 0;
  StrategyRunRequest? lastRequest;

  @override
  Future<CapabilitiesResponse> getCapabilities() async {
    capabilitiesCalls++;
    if (capabilitiesError != null) throw capabilitiesError!;
    return capabilitiesResult;
  }

  @override
  Future<StrategyRunResponse> run(
    StrategyRunRequest request, {
    CancelToken? cancelToken,
  }) async {
    runCalls++;
    lastRequest = request;
    if (runError != null) throw runError!;
    if (pendingRun != null) return pendingRun!.future;
    return runResult!;
  }
}
