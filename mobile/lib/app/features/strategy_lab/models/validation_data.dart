class ValidationData {
  const ValidationData({
    required this.valid,
    required this.syntaxValid,
    required this.importsValid,
    required this.securityValid,
    required this.interfaceValid,
    required this.lookaheadValid,
    required this.errors,
  });

  factory ValidationData.fromJson(Map<String, dynamic> json) {
    return ValidationData(
      valid: json['valid'] as bool,
      syntaxValid: json['syntax_valid'] as bool,
      importsValid: json['imports_valid'] as bool,
      securityValid: json['security_valid'] as bool,
      interfaceValid: json['interface_valid'] as bool,
      lookaheadValid: json['lookahead_valid'] as bool,
      errors: List<String>.unmodifiable(
        (json['errors'] as List).cast<String>(),
      ),
    );
  }

  final bool valid;
  final bool syntaxValid;
  final bool importsValid;
  final bool securityValid;
  final bool interfaceValid;
  final bool lookaheadValid;
  final List<String> errors;
}
