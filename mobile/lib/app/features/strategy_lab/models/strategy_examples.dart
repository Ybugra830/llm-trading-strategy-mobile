const strategyExamples = [
  (
    id: 'rsi',
    title: 'Düşüş ve yükseliş gücünü izle',
    description: 'RSI 30 altında alış, 70 üzerinde çıkış kuralını dener.',
    indicators: ['RSI'],
    terms: ['RSI'],
    published: true,
    prompt:
        'Günlük kapanışlardan RSI14 hesapla. RSI 30 altındaysa pozisyon yokken al; RSI 70 üzerindeyse açık pozisyonu kapat.',
  ),
  (
    id: 'sma',
    title: 'İki fiyat ortalamasının kesişimini izle',
    description:
        'Kısa ortalama uzun ortalamayı yukarı kesince alır, aşağı kesince çıkar.',
    indicators: ['SMA'],
    terms: ['SMA'],
    published: true,
    prompt:
        'Günlük kapanış fiyatlarından 20 periyotluk SMA ve 50 periyotluk SMA hesapla. SMA20, SMA50’yi yukarı keserse açık pozisyon yokken al. SMA20, SMA50’yi aşağı keserse açık pozisyonu kapat. Açık pozisyon varken yeni alım yapma.',
  ),
  (
    id: 'ema',
    title: 'Son fiyatlara daha fazla ağırlık ver',
    description:
        'Son fiyatlara daha duyarlı iki ortalamanın kesişimini kullanır.',
    indicators: ['EMA'],
    terms: ['EMA'],
    published: false,
    prompt:
        'Günlük kapanış fiyatlarından 10 periyotluk EMA ve 30 periyotluk EMA hesapla. EMA10, EMA30’u yukarı keserse açık pozisyon yokken al. EMA10, EMA30’u aşağı keserse açık pozisyonu kapat. Açık pozisyon varken yeni alım yapma.',
  ),
  (
    id: 'macd',
    title: 'Fiyat hareketinin gücündeki değişimi izle',
    description:
        'MACD çizgisinin sinyal çizgisini kesmesine göre giriş ve çıkış yapar.',
    indicators: ['MACD'],
    terms: ['MACD'],
    published: false,
    prompt:
        'Günlük kapanış fiyatlarından MACD hesapla: hızlı EMA 12 periyot, yavaş EMA 26 periyot, sinyal çizgisi 9 periyot olsun. MACD çizgisi sinyal çizgisini yukarı keserse açık pozisyon yokken al. MACD çizgisi sinyal çizgisini aşağı keserse açık pozisyonu kapat. Açık pozisyon varken yeni alım yapma.',
  ),
  (
    id: 'bollinger',
    title: 'Fiyatı değişen bantlarla karşılaştır',
    description:
        'Kapanış alt bandın altında olduğunda alır, üst bandın üzerine çıktığında çıkar.',
    indicators: ['Bollinger Bands'],
    terms: ['Bollinger'],
    published: false,
    prompt:
        'Günlük kapanış fiyatlarından 20 periyot ve 2 standart sapma ile Bollinger bantlarını hesapla. Kapanış fiyatı alt banttan küçükse açık pozisyon yokken al. Kapanış fiyatı üst banttan büyükse açık pozisyonu kapat. Bantlara eşitlik tek başına alış veya çıkış koşulunu sağlamaz. Açık pozisyon varken yeni alım yapma.',
  ),
  (
    id: 'stochastic',
    title: 'Fiyat son dönem aralığında nerede?',
    description:
        'Stochastic %K 20 altında alış, 80 üzerinde çıkış kuralını dener.',
    indicators: ['Stochastic'],
    terms: ['Stochastic'],
    published: false,
    prompt:
        'Günlük fiyatlardan Stochastic hesapla: pencere 14 periyot, sinyal yumuşatma 3 periyot olsun. %K 20’den küçükse açık pozisyon yokken al. %K 80’den büyükse açık pozisyonu kapat. Açık pozisyon varken yeni alım yapma.',
  ),
  (
    id: 'combined',
    title: 'İki koşulu birlikte dene',
    description:
        'Alış için hem RSI hem fiyat ortalaması koşulunu arar; çıkışta iki koşuldan biri yeterlidir.',
    indicators: ['RSI', 'SMA'],
    terms: ['RSI', 'SMA'],
    published: false,
    prompt:
        'Günlük kapanış fiyatlarından 14 periyotluk RSI ve 20 periyotluk SMA hesapla. RSI 30’dan küçük VE kapanış fiyatı SMA20’den büyükse açık pozisyon yokken al. RSI 70’den büyük VEYA kapanış fiyatı SMA20’den küçükse açık pozisyonu kapat. Açık pozisyon varken yeni alım yapma.',
  ),
];

const companyNames = {
  'THYAO': 'Türk Hava Yolları',
  'ASELS': 'Aselsan',
  'TUPRS': 'Tüpraş',
  'BIMAS': 'BİM',
  'EREGL': 'Ereğli Demir Çelik',
  'KCHOL': 'Koç Holding',
  'GARAN': 'Garanti BBVA',
  'AKBNK': 'Akbank',
  'SISE': 'Şişecam',
  'SAHOL': 'Sabancı Holding',
  'FROTO': 'Ford Otosan',
  'TOASO': 'Tofaş',
};
String companyLabel(String symbol) => companyNames.containsKey(symbol)
    ? '${companyNames[symbol]} ($symbol)'
    : symbol;
