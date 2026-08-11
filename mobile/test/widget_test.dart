import 'package:flutter_test/flutter_test.dart';
import 'package:llm_trading_strategy_mobile/app.dart';

void main() {
  testWidgets('başlangıç ekranını gösterir', (WidgetTester tester) async {
    await tester.pumpWidget(const TradingStrategyApp());

    expect(find.text('LLM Trading Strategy Mobile'), findsOneWidget);
    expect(find.text('Proje altyapısı hazır.'), findsOneWidget);
  });
}
