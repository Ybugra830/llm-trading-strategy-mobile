import 'package:dio/dio.dart';
import 'dart:typed_data';

Map<String, dynamic> capabilitiesJson() => {
  'supported_symbols': ['THYAO', 'ASELS'],
  'supported_indicators': ['RSI', 'MACD'],
  'defaults': {'initial_cash': 100000, 'commission': 0.002},
  'prompt': {'min_length': 5, 'max_length': 2000},
};

Map<String, dynamic> runResponseJson({bool nullableProfitFactor = false}) => {
  'status': 'success',
  'generation': {
    'model': 'test/model',
    'attempt_count': 2,
    'repaired': true,
    'code': 'class GeneratedStrategy:\n    pass',
  },
  'validation': {
    'valid': true,
    'syntax_valid': true,
    'imports_valid': true,
    'security_valid': true,
    'interface_valid': true,
    'lookahead_valid': true,
    'errors': <String>[],
  },
  'runtime': {'sandboxed': true, 'smoke_test_passed': true},
  'symbol': 'THYAO',
  'yahoo_symbol': 'THYAO.IS',
  'data': {
    'download_start': '2023-01-01',
    'download_end': '2026-01-01',
    'total_rows': 780,
    'history_rows': 650,
    'test_rows': 130,
    'cutoff_date': '2025-07-01',
    'test_start': '2025-07-01',
    'test_end': '2026-01-01',
  },
  'configuration': {'initial_cash': 100000, 'commission': 0.002},
  'metrics': {
    'initial_cash': 100000,
    'final_equity': 101234.56,
    'net_profit': 1234.56,
    'return_percent': 1.23456,
    'buy_and_hold_return_percent': 2.5,
    'number_of_trades': 3,
    'win_rate_percent': 66.67,
    'max_drawdown_percent': -1.25,
    'sharpe_ratio': 1.2,
    'sortino_ratio': 1.8,
    'profit_factor': nullableProfitFactor ? null : 2.1,
    'best_trade_percent': 3.2,
    'worst_trade_percent': -1.1,
    'average_trade_duration': '2 days 00:00:00',
    'exposure_time_percent': 20.5,
  },
};

class StubHttpClientAdapter implements HttpClientAdapter {
  StubHttpClientAdapter(this.handler);

  final Future<ResponseBody> Function(RequestOptions options) handler;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) {
    return handler(options);
  }

  @override
  void close({bool force = false}) {}
}
