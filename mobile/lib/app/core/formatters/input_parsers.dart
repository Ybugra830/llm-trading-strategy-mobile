bool hasAmbiguousGrouping(String value) =>
    RegExp(r'^[+-]?\d{1,3}\.\d{3}$').hasMatch(value.trim());

double? parseNumber(String value) {
  final text = value.trim();
  if (!RegExp(
    r'^[+-]?(?:\d+(?:[.,]\d+)?|[.,]\d+)(?:[eE][+-]?\d+)?$',
  ).hasMatch(text)) {
    return null;
  }
  final number = double.tryParse(text.replaceAll(',', '.'));
  return number != null && number.isFinite ? number : null;
}

double? parseCash(String value) =>
    hasAmbiguousGrouping(value) ? null : parseNumber(value);

double? percentTextToDecimal(String value) {
  final text = value.trim();
  final percent = parseNumber(
    text.endsWith('%') ? text.substring(0, text.length - 1) : text,
  );
  return percent == null ? null : percent / 100;
}

String decimalToPercentText(double value) {
  final text = (value * 100).toString();
  if (text.contains('e')) return text.replaceAll('.', ',');
  final parts = text.split('.');
  return '${parts.first},${(parts.length > 1 ? parts.last : '').padRight(2, '0')}';
}
