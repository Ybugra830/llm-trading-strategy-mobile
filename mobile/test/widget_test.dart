import 'package:flutter_test/flutter_test.dart';
import 'package:llm_trading_strategy_mobile/app/app.dart';

void main() {
  testWidgets('başlangıç ekranını gösterir', (WidgetTester tester) async {
    await tester.pumpWidget(const TradingStrategyApp());

    expect(find.text('LLM Trading Strategy'), findsOneWidget);
    expect(find.text('Proje iskeleti hazır'), findsOneWidget);
  });
}
