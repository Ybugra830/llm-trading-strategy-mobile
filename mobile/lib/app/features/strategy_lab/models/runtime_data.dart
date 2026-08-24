class RuntimeData {
  const RuntimeData({required this.sandboxed, required this.smokeTestPassed});

  factory RuntimeData.fromJson(Map<String, dynamic> json) {
    return RuntimeData(
      sandboxed: json['sandboxed'] as bool,
      smokeTestPassed: json['smoke_test_passed'] as bool,
    );
  }

  final bool sandboxed;
  final bool smokeTestPassed;
}
