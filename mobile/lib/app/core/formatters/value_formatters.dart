import 'package:intl/intl.dart';

final _money = NumberFormat('#,##0.00', 'en_US');
final _date = DateFormat('MMM d, y', 'en_US');

String formatMoney(double? value) =>
    value == null ? 'N/A' : '${_money.format(value)} TRY';

String formatNumber(double? value, {int digits = 2}) =>
    value == null ? 'N/A' : value.toStringAsFixed(digits);

String formatPercent(double? value, {bool signed = false}) {
  if (value == null) return 'N/A';
  final prefix = signed && value > 0 ? '+' : '';
  return '$prefix${value.toStringAsFixed(2)}%';
}

String formatDateRange(DateTime start, DateTime end) =>
    '${_date.format(start)} – ${_date.format(end)}';
