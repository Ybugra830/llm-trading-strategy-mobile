import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../../../core/formatters/input_parsers.dart';
import '../data/strategy_lab_repository.dart';
import '../models/capabilities_response.dart';
import '../models/strategy_lab_failure.dart';
import '../models/strategy_run_request.dart';
import '../models/strategy_run_response.dart';
import 'strategy_lab_state.dart';

class StrategyLabController extends ChangeNotifier {
  StrategyLabController(this._repository);

  final StrategyLabRepository _repository;
  int _requestId = 0;
  CancelToken? _cancelToken;

  CapabilitiesStatus capabilitiesStatus = CapabilitiesStatus.initial;
  StrategyRunStatus runStatus = StrategyRunStatus.idle;
  CapabilitiesResponse? capabilities;
  StrategyRunResponse? response;
  StrategyLabFailure? failure;
  StrategyInputDraft draft = const StrategyInputDraft();
  StrategyInputValidation validation = const StrategyInputValidation();

  bool get isSubmitting => runStatus == StrategyRunStatus.loading;

  Future<void> loadCapabilities() async {
    if (capabilitiesStatus == CapabilitiesStatus.loading) return;
    capabilitiesStatus = CapabilitiesStatus.loading;
    failure = null;
    notifyListeners();
    try {
      final loaded = await _repository.getCapabilities();
      capabilities = loaded;
      if (draft.symbol.isEmpty) {
        draft = draft.copyWith(
          symbol: loaded.supportedSymbols.first,
          initialCash: _plainNumber(loaded.defaults.initialCash),
          commissionPercent: decimalToPercentText(loaded.defaults.commission),
        );
      }
      capabilitiesStatus = CapabilitiesStatus.ready;
    } on StrategyLabException catch (error) {
      failure = error.failure;
      capabilitiesStatus = CapabilitiesStatus.error;
    }
    notifyListeners();
  }

  void updatePrompt(String value) {
    draft = draft.copyWith(prompt: value);
    if (validation.prompt != null) {
      validation = const StrategyInputValidation();
    }
    notifyListeners();
  }

  void updateSymbol(String value) {
    draft = draft.copyWith(symbol: value);
    notifyListeners();
  }

  void updateInitialCash(String value) {
    draft = draft.copyWith(initialCash: value);
    notifyListeners();
  }

  void updateCommissionPercent(String value) {
    draft = draft.copyWith(commissionPercent: value);
    notifyListeners();
  }

  Future<StrategyRunOutcome?> run() async {
    if (isSubmitting || capabilitiesStatus != CapabilitiesStatus.ready) {
      return null;
    }
    final request = _buildRequest();
    if (request == null) {
      notifyListeners();
      return null;
    }

    final requestId = ++_requestId;
    final cancelToken = CancelToken();
    _cancelToken = cancelToken;
    runStatus = StrategyRunStatus.loading;
    response = null;
    failure = null;
    notifyListeners();

    try {
      final result = await _repository.run(request, cancelToken: cancelToken);
      if (requestId != _requestId) return null;
      response = result;
      runStatus = StrategyRunStatus.success;
      final outcome = StrategyRunOutcome.success(result);
      notifyListeners();
      return outcome;
    } on StrategyLabException catch (error) {
      if (requestId != _requestId ||
          error.failure.type == StrategyLabFailureType.cancelled) {
        return null;
      }
      failure = error.failure;
      runStatus = _statusFor(error.failure.type);
      final outcome = StrategyRunOutcome.failure(error.failure);
      notifyListeners();
      return outcome;
    } finally {
      if (requestId == _requestId) _cancelToken = null;
    }
  }

  void cancelRun() {
    if (!isSubmitting) return;
    _requestId++;
    _cancelToken?.cancel('Cancelled by user');
    _cancelToken = null;
    runStatus = StrategyRunStatus.idle;
    failure = null;
    notifyListeners();
  }

  void returnToInput() {
    if (isSubmitting) cancelRun();
    runStatus = StrategyRunStatus.idle;
    response = null;
    failure = null;
    notifyListeners();
  }

  StrategyRunRequest? _buildRequest() {
    final limits = capabilities?.prompt;
    final prompt = draft.prompt.trim();
    final cash = parseNumber(draft.initialCash);
    final commission = percentTextToDecimal(draft.commissionPercent);
    final promptError = limits == null || prompt.length < limits.minLength
        ? 'Enter at least ${limits?.minLength ?? 5} characters.'
        : prompt.length > limits.maxLength
        ? 'Use no more than ${limits.maxLength} characters.'
        : null;
    final symbolError =
        capabilities?.supportedSymbols.contains(draft.symbol) == true
        ? null
        : 'Select a supported BIST symbol.';
    final cashError = cash != null && cash > 0
        ? null
        : 'Enter a positive initial cash value.';
    final commissionError =
        commission != null && commission >= 0 && commission < 0.1
        ? null
        : 'Commission must be between 0% and 10%.';

    validation = StrategyInputValidation(
      prompt: promptError,
      symbol: symbolError,
      initialCash: cashError,
      commission: commissionError,
    );
    if (!validation.isValid) return null;
    return StrategyRunRequest(
      prompt: prompt,
      symbol: draft.symbol,
      initialCash: cash!,
      commission: commission!,
    );
  }

  static StrategyRunStatus _statusFor(StrategyLabFailureType type) {
    return switch (type) {
      StrategyLabFailureType.validation => StrategyRunStatus.validationError,
      StrategyLabFailureType.provider => StrategyRunStatus.providerError,
      StrategyLabFailureType.sandbox => StrategyRunStatus.sandboxError,
      StrategyLabFailureType.backend => StrategyRunStatus.backendError,
      StrategyLabFailureType.network => StrategyRunStatus.networkError,
      StrategyLabFailureType.unknown ||
      StrategyLabFailureType.cancelled => StrategyRunStatus.unknownError,
    };
  }

  static String _plainNumber(double value) {
    return value == value.roundToDouble()
        ? value.toInt().toString()
        : value.toString();
  }

  @override
  void dispose() {
    _cancelToken?.cancel('Controller disposed');
    super.dispose();
  }
}
