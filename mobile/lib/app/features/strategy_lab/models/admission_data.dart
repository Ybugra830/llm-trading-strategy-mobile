class AdmissionData {
  const AdmissionData({required this.defaultsApplied});

  factory AdmissionData.fromJson(Map<String, dynamic> json) {
    if (json['decision'] != 'accepted') {
      throw const FormatException('Unexpected admission decision.');
    }
    final defaults = (json['defaults_applied'] as List).map((item) {
      final data = Map<String, dynamic>.from(item as Map);
      const labels = {
        'window': 'periyot',
        'window_fast': 'hızlı periyot',
        'window_slow': 'yavaş periyot',
        'window_signal': 'sinyal periyodu',
        'smooth_window': 'yumuşatma',
        'deviation': 'sapma',
      };
      final parameter = labels[data['parameter']] ?? data['parameter'];
      return '${(data['family'] as String).toUpperCase()} '
          '(${data['indicator_id']}): $parameter = ${data['value']}';
    }).toList();
    return AdmissionData(defaultsApplied: defaults);
  }

  final List<String> defaultsApplied;
}
