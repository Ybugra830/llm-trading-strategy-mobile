import 'package:flutter/material.dart';

const termDefinitions = <String, String>{
  'Hisse':
      'Bir şirketin ortaklık payıdır. Burada seçtiğiniz hissenin geçmiş fiyatlarıyla simülasyon yapılır.',
  'Borsa':
      'Hisse gibi varlıkların alınıp satıldığı piyasadır. Bu uygulama yalnız listelenen BIST hisselerini destekler.',
  'Strateji':
      'Ne zaman alım yapılacağını ve pozisyonun ne zaman kapatılacağını belirleyen kurallardır.',
  'Gösterge':
      'Geçmiş fiyat veya hacimden hesaplanan yardımcı ölçüdür. Gelecekteki fiyatı kesin olarak tahmin etmez.',
  'Açılış / kapanış':
      'Bir işlem gününün başlangıç ve bitiş fiyatlarıdır. Normal alış/kapatma sinyalleri sonraki işlem gününün açılışında uygulanır.',
  'Günlük veri':
      'Her kayıt bir işlem gününün açılış, en yüksek, en düşük, kapanış fiyatı ve hacmini içerir.',
  'Açık pozisyon': 'Simülasyonda alınmış ve henüz satılmamış hisselerdir.',
  'Pozisyon kapatma':
      'Eldeki pozisyonu satarak işlemi bitirmektir; açığa satış yapmak değildir.',
  'Periyot':
      'Günlük veride hesaplamaya katılan işlem günü sayısıdır. 20 periyot, 20 takvim günü değildir.',
  'Kesişim':
      'Bir çizginin diğerinin bir tarafından öbür tarafına geçmesidir. Üstünde olmak tek başına yukarı kesişim değildir; önceki değer eşit/altındayken yeni değer üstüne çıkar.',
  'SMA': 'Son belirli sayıdaki kapanış fiyatının basit ortalamasıdır.',
  'EMA': 'Son fiyatlara daha fazla ağırlık veren ortalamadır.',
  'RSI':
      'Son yükseliş ve düşüşlerin göreli gücünü 0–100 aralığında özetler. 30 veya 70 tek başına kesin dönüş anlamına gelmez.',
  'MACD': 'Kısa ve uzun EMA arasındaki farkı sinyal çizgisiyle karşılaştırır.',
  'Bollinger':
      'Fiyat ortalamasının çevresinde, değişkenliğe göre genişleyen veya daralan bantlardır.',
  'ATR':
      'Günlük fiyat hareketinin büyüklüğünü ölçer; yükseliş veya düşüş yönünü söylemez. Fiyatla aynı birimdedir.',
  'Stochastic':
      'Kapanışın yakın geçmişteki en yüksek ve en düşük fiyatlar arasındaki konumunu gösterir. %K bu konumu, 3 periyot ise sinyal çizgisinin yumuşatmasını ifade eder.',
  'Komisyon':
      'İşlem tutarı üzerinden alınan maliyettir. Simülasyonda alışta ve satışta ayrı hesaplanır.',
  'Geçmiş veri testi':
      'Kuralların geçmiş fiyatlarda nasıl sonuç verdiğini hesaplayan simülasyondur. Gelecekte aynı sonucun oluşacağını göstermez.',
  'Başlangıç sermayesi': 'Simülasyonun başladığı sanal tutardır.',
  'Son portföy değeri':
      'Test sonunda simülasyonda kalan toplam değerdir; uygulanan komisyonlar hesaba dahildir.',
  'Net kâr/zarar':
      'Son portföy değeri ile başlangıç tutarı arasındaki TL farkıdır.',
  'Toplam getiri': 'Başlangıç tutarına göre portföyün yüzde değişimidir.',
  'Tamamlanan işlem':
      'Alış ve kapanıştan oluşan tamamlanmış pozisyon sayısıdır; emir sayısı değildir. Test sonunda zorunlu kapatılan pozisyonlar da dahildir.',
  'Al-tut getirisi':
      'Gösterge başlangıç verisi oluştuktan sonraki referans kapanıştan son kapanışa fiyat değişimidir. Komisyon içermez; strateji getirisi komisyon içerir.',
  'Maksimum düşüş':
      'Portföyün test sırasında ulaştığı bir tepeden sonraki en büyük yüzde gerilemesidir. Başlangıca göre zarar ile aynı şey değildir.',
  'Kazanma oranı': 'Kârla kapanan işlemlerin tamamlanan işlemlere oranıdır.',
  'Sharpe':
      'Motorun getiri ile portföy dalgalanmasını birlikte değerlendiren ölçüsüdür. Tek başına strateji seçmek için yeterli değildir.',
  'Sortino':
      'Getiriyi aşağı yönlü dalgalanmayla birlikte değerlendiren ölçüdür.',
  'Kâr faktörü':
      'Kazançlı işlemlerin toplam kazancının, zararlı işlemlerin toplam kaybına oranıdır.',
  'En iyi işlem': 'Tamamlanan işlemler arasındaki en yüksek yüzde getiridir.',
  'En kötü işlem': 'Tamamlanan işlemler arasındaki en düşük yüzde getiridir.',
  'Ortalama işlem süresi':
      'Tamamlanan pozisyonların ortalama açık kalma süresidir.',
  'Pozisyonda kalınan süre':
      'Test döneminin ne kadarında açık pozisyon bulunduğunu gösterir.',
  'Test kapsamı':
      'Yalnız listelenen BIST hisseleri, tamamlanmış günlük veri ve alış yönünde pozisyonlar desteklenir. Açığa satış, kaldıraç ve gün içi işlem desteklenmez. Test, son mevcut veri tarihinden geriye altı takvim ayını kullanır; kesin tarihler sonuçta gösterilir. Göstergelerin başlangıç verisi ihtiyacı nedeniyle bütün günlerde işlem oluşmayabilir.',
  'Testin sınırları':
      'Test sonunda kalan pozisyonlar motor tarafından son mumun açılış fiyatında kapatılır. Strateji getirisi alış ve satış komisyonunu içerir; ayrıca fiyat kayması veya hacme bağlı piyasa etkisi modellenmez.',
};

Future<void> showExplanation(
  BuildContext context,
  String title,
  Widget content,
) {
  final body = Column(
    mainAxisSize: MainAxisSize.min,
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Text(title, style: Theme.of(context).textTheme.titleLarge),
      const SizedBox(height: 16),
      content,
      const SizedBox(height: 16),
      Align(
        alignment: Alignment.centerRight,
        child: TextButton(
          style: TextButton.styleFrom(
            foregroundColor: Theme.of(context).colorScheme.onSurface,
          ),
          onPressed: () => Navigator.pop(context),
          child: const Text('Kapat'),
        ),
      ),
    ],
  );
  if (MediaQuery.sizeOf(context).width < 700) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (_) => ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.sizeOf(context).height * .9,
        ),
        child: SingleChildScrollView(
          padding: EdgeInsets.fromLTRB(
            24,
            24,
            24,
            24 + MediaQuery.viewInsetsOf(context).bottom,
          ),
          child: body,
        ),
      ),
    );
  }
  return showDialog<void>(
    context: context,
    builder: (_) => AlertDialog(
      content: SizedBox(width: 560, child: SingleChildScrollView(child: body)),
    ),
  );
}

class TermHelp extends StatelessWidget {
  const TermHelp(this.term, {super.key});
  final String term;
  @override
  Widget build(BuildContext context) => IconButton(
    tooltip: '$term: Bu ne demek?',
    constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
    onPressed: () =>
        showExplanation(context, term, Text(termDefinitions[term]!)),
    icon: const Icon(Icons.info_outline, size: 20),
  );
}

void showFirstUseGuide(BuildContext context) => showExplanation(
  context,
  'İlk kez kullanıyorum',
  const Text(
    '1. Örnek seç veya kuralını yaz.\nNe zaman alım yapılacağını ve açık pozisyonun ne zaman kapatılacağını belirt. Örneği seçtikten sonra değiştirebilirsin.\n\n'
    '2. Hisse ve tutarı belirle.\nListeden hisse seç. Sanal başlangıç tutarını ve alışta/satışta uygulanacak komisyonu kontrol et. Gerçek para veya emir kullanılmaz.\n\n'
    '3. Sonucu incele.\nGeçmiş veride test et düğmesine bas. Sonuçtaki kâr/zararı, işlem sayısını ve açıklamaları birlikte incele. Geçmiş sonuç gelecek kazancını göstermez.',
  ),
);
