class StrategyLabDefaults {
  const StrategyLabDefaults({
    required this.initialCash,
    required this.commission,
  });

  factory StrategyLabDefaults.fromJson(Map<String, dynamic> json) {
    return StrategyLabDefaults(
      initialCash: (json['initial_cash'] as num).toDouble(),
      commission: (json['commission'] as num).toDouble(),
    );
  }

  final double initialCash;
  final double commission;
}

class StrategyPromptLimits {
  const StrategyPromptLimits({
    required this.minLength,
    required this.maxLength,
  });

  factory StrategyPromptLimits.fromJson(Map<String, dynamic> json) {
    return StrategyPromptLimits(
      minLength: json['min_length'] as int,
      maxLength: json['max_length'] as int,
    );
  }

  final int minLength;
  final int maxLength;
}

class CapabilitiesResponse {
  const CapabilitiesResponse({
    required this.supportedSymbols,
    required this.supportedIndicators,
    required this.defaults,
    required this.prompt,
  });

  factory CapabilitiesResponse.fromJson(Map<String, dynamic> json) {
    return CapabilitiesResponse(
      supportedSymbols: List<String>.unmodifiable(
        (json['supported_symbols'] as List).cast<String>(),
      ),
      supportedIndicators: List<String>.unmodifiable(
        (json['supported_indicators'] as List).cast<String>(),
      ),
      defaults: StrategyLabDefaults.fromJson(
        Map<String, dynamic>.from(json['defaults'] as Map),
      ),
      prompt: StrategyPromptLimits.fromJson(
        Map<String, dynamic>.from(json['prompt'] as Map),
      ),
    );
  }

  final List<String> supportedSymbols;
  final List<String> supportedIndicators;
  final StrategyLabDefaults defaults;
  final StrategyPromptLimits prompt;
}
