import 'package:flutter_test/flutter_test.dart';
import 'package:llm_trading_strategy_mobile/app/core/formatters/input_parsers.dart';

void main() {
  test('converts displayed commission percent to API decimal', () {
    expect(percentTextToDecimal('0.20'), closeTo(0.002, 0.0000001));
    expect(percentTextToDecimal('0,20%'), closeTo(0.002, 0.0000001));
    expect(decimalToPercentText(0.002), '0.20');
  });
}
