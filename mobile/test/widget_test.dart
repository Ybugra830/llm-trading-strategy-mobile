import 'package:flutter_test/flutter_test.dart';
import 'package:llm_trading_strategy_mobile/app/core/formatters/input_parsers.dart';

void main() {
  test('uygulama komisyon yüzdesini API oranına dönüştürür', () {
    expect(percentTextToDecimal('0.20'), 0.002);
  });
}
