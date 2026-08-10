import 'package:flutter/material.dart';

class TradingStrategyApp extends StatelessWidget {
  const TradingStrategyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'LLM Trading Strategy',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.indigo),
        useMaterial3: true,
      ),
      home: Scaffold(
        appBar: AppBar(
          title: const Text('LLM Trading Strategy'),
        ),
        body: const Center(
          child: Text('Proje iskeleti hazır'),
        ),
      ),
    );
  }
}
