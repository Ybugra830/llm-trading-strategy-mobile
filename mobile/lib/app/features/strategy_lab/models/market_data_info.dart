class MarketDataInfo {
  const MarketDataInfo({
    required this.downloadStart,
    required this.downloadEnd,
    required this.totalRows,
    required this.historyRows,
    required this.testRows,
    required this.cutoffDate,
    required this.testStart,
    required this.testEnd,
  });

  factory MarketDataInfo.fromJson(Map<String, dynamic> json) {
    return MarketDataInfo(
      downloadStart: DateTime.parse(json['download_start'] as String),
      downloadEnd: DateTime.parse(json['download_end'] as String),
      totalRows: json['total_rows'] as int,
      historyRows: json['history_rows'] as int,
      testRows: json['test_rows'] as int,
      cutoffDate: DateTime.parse(json['cutoff_date'] as String),
      testStart: DateTime.parse(json['test_start'] as String),
      testEnd: DateTime.parse(json['test_end'] as String),
    );
  }

  final DateTime downloadStart;
  final DateTime downloadEnd;
  final int totalRows;
  final int historyRows;
  final int testRows;
  final DateTime cutoffDate;
  final DateTime testStart;
  final DateTime testEnd;
}
