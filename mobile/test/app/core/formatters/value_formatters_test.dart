import 'package:flutter_test/flutter_test.dart';
import 'package:llm_trading_strategy_mobile/app/core/formatters/value_formatters.dart';

void main() {
  test('Turkish values distinguish missing, zero and signed loss', () {
    expect(formatMoney(100000.75), '100.000,75 TL');
    expect(formatMoney(null), 'Hesaplanamadı');
    expect(formatPercent(0), '%0,00');
    expect(formatPercent(-12, signed: true), '−%12,00');
    expect(formatPercent(12, signed: true), '+%12,00');
    expect(formatNumber(1.234), '1,23');
    expect(formatDuration('2 days 04:30:00'), '2 gün 4 saat 30 dakika');
    expect(formatDuration('unexpected'), 'Hesaplanamadı');
    expect(
      formatDateRange(DateTime(2026, 4, 16), DateTime(2026, 10, 16)),
      '16.04.2026 – 16.10.2026',
    );
  });
}
