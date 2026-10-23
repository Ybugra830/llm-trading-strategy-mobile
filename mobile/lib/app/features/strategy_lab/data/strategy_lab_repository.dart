import 'package:dio/dio.dart';

import '../../../core/api/api_exception.dart';
import '../models/capabilities_response.dart';
import '../models/strategy_lab_failure.dart';
import '../models/strategy_run_request.dart';
import '../models/strategy_run_response.dart';
import 'strategy_lab_api.dart';

abstract interface class StrategyLabRepository {
  Future<CapabilitiesResponse> getCapabilities();

  Future<StrategyRunResponse> run(
    StrategyRunRequest request, {
    CancelToken? cancelToken,
  });
}

class HttpStrategyLabRepository implements StrategyLabRepository {
  const HttpStrategyLabRepository(this._api);

  final StrategyLabApi _api;

  @override
  Future<CapabilitiesResponse> getCapabilities() async {
    try {
      final response = await _api.getCapabilities();
      if (response.supportedSymbols.isEmpty ||
          response.supportedIndicators.isEmpty ||
          !response.defaults.initialCash.isFinite ||
          response.defaults.initialCash <= 0 ||
          !response.defaults.commission.isFinite ||
          response.defaults.commission < 0 ||
          response.defaults.commission >= .1 ||
          response.prompt.minLength < 1 ||
          response.prompt.maxLength < response.prompt.minLength) {
        throw const StrategyLabException(
          StrategyLabFailure(
            type: StrategyLabFailureType.unknown,
            message: 'Hisse ve test ayarları eksik. Yeniden deneyin.',
          ),
        );
      }
      return response;
    } on StrategyLabException {
      rethrow;
    } on ApiException catch (error) {
      throw StrategyLabException(_mapApiError(error));
    } on Object {
      throw const StrategyLabException(
        StrategyLabFailure(
          type: StrategyLabFailureType.unknown,
          message:
              'Sunucudan beklenmeyen bir yanıt alındı. Girdileriniz korundu.',
        ),
      );
    }
  }

  @override
  Future<StrategyRunResponse> run(
    StrategyRunRequest request, {
    CancelToken? cancelToken,
  }) async {
    try {
      return await _api.run(request, cancelToken: cancelToken);
    } on ApiException catch (error) {
      throw StrategyLabException(_mapApiError(error));
    } on Object {
      throw const StrategyLabException(
        StrategyLabFailure(
          type: StrategyLabFailureType.unknown,
          message:
              'Sunucudan beklenmeyen bir yanıt alındı. Girdileriniz korundu.',
        ),
      );
    }
  }

  static StrategyLabFailure _mapApiError(ApiException error) {
    if (error.kind == ApiExceptionKind.cancelled) {
      return const StrategyLabFailure(
        type: StrategyLabFailureType.cancelled,
        message: 'Bekleme sonlandırıldı.',
      );
    }
    if (error.kind == ApiExceptionKind.network ||
        error.kind == ApiExceptionKind.timeout) {
      return StrategyLabFailure(
        type: StrategyLabFailureType.network,
        message: error.kind == ApiExceptionKind.timeout
            ? 'Yanıt bekleme süresi doldu. Sunucudaki işlem devam ediyor olabilir. Girdileriniz korundu.'
            : 'Hizmete bağlanılamadı. Bağlantınızı kontrol edip yeniden deneyin.',
      );
    }
    final detail = error.safeDetail;
    if ((error.statusCode == 422 &&
            detail == 'Backtest için yeterli piyasa verisi bulunamadı.') ||
        (error.statusCode == 502 &&
            detail == 'Piyasa verisi şu anda kullanılamıyor.')) {
      return const StrategyLabFailure(
        type: StrategyLabFailureType.marketData,
        message:
            'Bu hisse için test yapmaya yeterli geçmiş veri alınamadı. Biraz sonra yeniden deneyebilir veya hisseyi değiştirebilirsiniz.',
      );
    }
    switch (error.statusCode) {
      case 422:
        const messages = {
          'NON_STRATEGY': 'Alım ve çıkış kurallarınızı yazın.',
          'INSTRUCTION_OVERRIDE':
              'Sistem talimatları yerine alım ve çıkış kurallarınızı yazın.',
          'PROFIT_GUARANTEE':
              'Kesin kazanç garanti edilemez. Test edilecek alım ve çıkış kurallarını belirtin.',
          'UNSUPPORTED': 'Bu özellik şu anda desteklenmiyor.',
          'INCOMPLETE':
              'Stratejiyi çalıştırmak için işlem kurallarını netleştirmeniz gerekiyor.',
          'CONTRADICTORY':
              'Stratejide çelişkili veya belirsiz kurallar var. Alım ve çıkış koşullarını netleştirin.',
          'INVALID_PARAMETERS':
              'Gösterge parametreleri veya eşikler geçersiz. Geçerli değerleri belirtin.',
        };
        const questions = {
          'Hangi koşulda alım yapılmalı?',
          'Hangi koşulda pozisyon kapatılmalı?',
          'Hangi sayısal eşik kullanılmalı?',
          'Hangi değerler, hangi yönde karşılaştırılmalı?',
          'Hangi gösterge veya fiyat serisi kullanılmalı?',
          'Belirsiz gösterge parametresinin değerini belirtir misiniz?',
          'İz süren zarar durdur yüzdesi kaç olmalı?',
        };
        return StrategyLabFailure(
          type: StrategyLabFailureType.validation,
          message:
              messages[error.reasonCode] ??
              (detail == 'Desteklenmeyen BIST sembolü.'
                  ? 'Listeden desteklenen bir BIST hissesi seçin.'
                  : 'Kurallarınızdan çalıştırılabilir bir strateji oluşturulamadı. Metni düzenleyebilir veya yeniden deneyebilirsiniz.'),
          decision: error.decision,
          reasonCode: error.reasonCode,
          questions: error.questions.where(questions.contains).toList(),
        );
      case 502:
        return const StrategyLabFailure(
          type: StrategyLabFailureType.provider,
          message:
              'Strateji şu anda oluşturulamıyor. Kurallarınız korundu; biraz sonra yeniden deneyebilirsiniz.',
        );
      case 503:
        return const StrategyLabFailure(
          type: StrategyLabFailureType.sandbox,
          message: 'Test ortamı şu anda kullanılamıyor. Girdileriniz korundu.',
        );
      case 500:
        return const StrategyLabFailure(
          type: StrategyLabFailureType.backend,
          message: 'Test şu anda tamamlanamadı. Girdileriniz korundu.',
        );
      default:
        return const StrategyLabFailure(
          type: StrategyLabFailureType.unknown,
          message:
              'Test tamamlanamadı. Girdileriniz korundu; biraz sonra yeniden deneyebilirsiniz.',
        );
    }
  }
}
