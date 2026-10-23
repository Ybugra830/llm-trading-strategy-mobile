import 'package:flutter_test/flutter_test.dart';
import 'package:llm_trading_strategy_mobile/app/core/formatters/input_parsers.dart';

void main() {
  test(
    'cash parsing preserves decimals and rejects ambiguous or malformed values',
    () {
      for (final value in ['100000,75', '100000.75']) {
        expect(parseCash(value), 100000.75);
      }
      for (final value in [
        '100.000',
        '1.000',
        '1 2',
        'abc100',
        '1,2,3',
        '1e309',
        'NaN',
        'Infinity',
      ]) {
        expect(parseCash(value), isNull, reason: value);
      }
      expect(parseCash('1e10'), 1e10);
      expect(parseCash('-1'), -1);
      expect(percentTextToDecimal('0.002'), closeTo(.00002, 1e-10));
      expect(percentTextToDecimal('1%2'), isNull);
      expect(percentTextToDecimal('%0,20'), isNull);
    },
  );
  test('converts displayed commission percent to API decimal', () {
    expect(percentTextToDecimal('0.20'), closeTo(0.002, 0.0000001));
    expect(percentTextToDecimal('0,20%'), closeTo(0.002, 0.0000001));
    expect(decimalToPercentText(0.002), '0,20');
    expect(percentTextToDecimal(decimalToPercentText(0.002555)), 0.002555);
  });
}
