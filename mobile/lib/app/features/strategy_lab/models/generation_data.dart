class GenerationData {
  const GenerationData({
    required this.model,
    required this.attemptCount,
    required this.repaired,
    required this.code,
  });

  factory GenerationData.fromJson(Map<String, dynamic> json) {
    return GenerationData(
      model: json['model'] as String,
      attemptCount: json['attempt_count'] as int,
      repaired: json['repaired'] as bool,
      code: json['code'] as String,
    );
  }

  final String model;
  final int attemptCount;
  final bool repaired;
  final String code;
}
