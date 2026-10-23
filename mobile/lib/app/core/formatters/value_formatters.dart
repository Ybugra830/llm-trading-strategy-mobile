import 'package:intl/intl.dart';

const unavailableValue = 'Hesaplanamadı';
final _money = NumberFormat('#,##0.00', 'tr_TR');
String _date(DateTime value) =>
    '${value.day.toString().padLeft(2, '0')}.${value.month.toString().padLeft(2, '0')}.${value.year}';

String formatMoney(double? value, {bool signed = false}) =>
    value == null || !value.isFinite
    ? unavailableValue
    : '${signed && value > 0 ? '+' : ''}${_money.format(value)} TL';

String formatNumber(double? value, {int digits = 2}) =>
    value == null || !value.isFinite
    ? unavailableValue
    : NumberFormat.decimalPatternDigits(
        locale: 'tr_TR',
        decimalDigits: digits,
      ).format(value);

String formatPercent(double? value, {bool signed = false}) {
  if (value == null || !value.isFinite) return unavailableValue;
  final prefix = value < 0
      ? '−'
      : signed && value > 0
      ? '+'
      : '';
  return '$prefix%${formatNumber(value.abs())}';
}

String formatDateRange(DateTime start, DateTime end) =>
    '${_date(start)} – ${_date(end)}';

String formatDuration(String? value) {
  if (value == null) return unavailableValue;
  final match = RegExp(
    r'^(\d+) days? (\d{2}):(\d{2}):(\d{2})(?:\.\d+)?$',
  ).firstMatch(value);
  if (match == null) return unavailableValue;
  return '${int.parse(match[1]!)} gün ${int.parse(match[2]!)} saat ${int.parse(match[3]!)} dakika';
}
