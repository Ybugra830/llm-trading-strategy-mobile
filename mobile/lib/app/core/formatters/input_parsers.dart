double? parseNumber(String value) {
  final normalized = value.trim().replaceAll(' ', '').replaceAll(',', '.');
  return double.tryParse(normalized);
}

double? percentTextToDecimal(String value) {
  final percent = parseNumber(value.replaceAll('%', ''));
  return percent == null ? null : percent / 100;
}

String decimalToPercentText(double value) {
  return (value * 100).toStringAsFixed(2);
}
