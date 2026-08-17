# AST Tabanlı Statik Kod Doğrulaması

## AST nedir?

AST, **Abstract Syntax Tree** yani **Soyut Sözdizimi Ağacı** anlamına gelir.
Python kaynak kodunu, metindeki karakterlerden ziyade dilin yapısal öğeleriyle
temsil eder.

Örneğin şu kaynak kodu:

```python
x = 1 + 2
```

kavramsal olarak şu ağaca dönüşür:

```text
Assign
├── Name(x)
└── BinOp
    ├── Constant(1)
    └── Constant(2)
```

Burada:

- `Assign`, bir atama işlemini,
- `Name(x)`, atamanın hedefini,
- `BinOp`, iki değer arasındaki işlemi,
- `Constant(1)` ve `Constant(2)`, sabit sayıları temsil eder.

## `ast.parse()` ne yapar?

```python
import ast

tree = ast.parse("x = 1 + 2")
```

`ast.parse()`:

1. Kaynak metni Python sözdizimi kurallarına göre ayrıştırır.
2. Sözdizimi geçerliyse bir AST oluşturur.
3. Sözdizimi geçersizse `SyntaxError` üretir.

`ast.parse()` normal Python ifadelerini çalıştırmaz. Örnekteki toplama ve atama
gerçekleşmez; yalnızca bunların yapısal temsili oluşturulur.

Bu projede incelenen kaynak kod için `exec()`, `eval()`, `compile()`, subprocess
ve dinamik import kullanılmaz.

## Sözdizimi doğrulaması ve güvenlik doğrulaması

### Sözdizimi doğrulaması

Şu soruyu cevaplar:

> “Bu, geçerli bir Python kodu mu?”

Örneğin aşağıdaki kod geçersizdir çünkü sınıf tanımında `:` eksiktir:

```python
class GeneratedStrategy(Strategy)
    pass
```

### Güvenlik doğrulaması

Şu soruyu cevaplar:

> “Bu kod geçerli Python olsa bile uygulamamızın yasakladığı yapılar içeriyor mu?”

Örneğin:

```python
import os
```

geçerli Python sözdizimidir. Ancak projenin import allowlist'inde `os` olmadığı
için güvenlik politikasına göre geçersizdir.

Benzer şekilde:

```python
eval("1 + 1")
```

sözdizimsel olarak geçerlidir fakat `eval` çağrısı uygulama tarafından
yasaklanmıştır.

## Doğrulama aşamaları

```text
Kaynak kodu
    ↓
Basit Markdown fence temizliği
    ↓
Tek bir ast.parse() çağrısı
    ↓
Import allowlist kontrolü
    ↓
Yasaklı fonksiyon çağrıları
    ↓
GeneratedStrategy interface kontrolü
    ↓
Basit negatif shift kontrolü
    ↓
ValidationResponse
```

### Import politikası

Yalnızca şu kök modüller kabul edilir:

- `backtesting`
- `ta`
- `pandas`
- `numpy`

Alt modüllerde kök isim değerlendirilir. Örneğin `ta.momentum` için kök `ta`
olduğundan import kabul edilir. Göreli importlar ve listede olmayan bütün kök
modüller reddedilir.

### Interface politikası

Kaynak kodu modül seviyesinde:

- Tam olarak `GeneratedStrategy` adında bir sınıf,
- `Strategy` veya `backtesting.Strategy` tabanı,
- Doğrudan sınıf gövdesinde normal `init()` metodu,
- Doğrudan sınıf gövdesinde normal `next()` metodu

içermelidir.

### Basit look-ahead kontrolü

Literal negatif shift kullanımı işaretlenir:

```python
series.shift(-1)
series.shift(periods=-2)
```

Backtesting kullanımında mevcut veya yakın geçmiş değerlere erişebilen şu
indeksler yalnızca negatif oldukları için reddedilmez:

```python
series[-1]
series[-2]
```

Bu kontrol look-ahead bias'ı tamamen önlediğini iddia etmez; yalnızca açık bir
kalıbı statik olarak işaretler.

## Neden AST bir sandbox değildir?

AST doğrulaması yalnızca yazılmış kuralları kontrol eder. Python dinamik bir dil
olduğu için alias kullanımı, dolaylı çağrılar ve karmaşık veri akışları basit bir
AST allowlist'iyle eksiksiz biçimde analiz edilemez.

Bu nedenle:

> LLM çıktısı güvenilir uygulama kodu değildir.

> Bu aşamada üretilen kod çalıştırılmamaktadır.

Gelecekte kod çalıştırılacaksa ayrıca süreç izolasyonu, kaynak limitleri, zaman
aşımı, dosya ve ağ erişim sınırları gibi sandbox önlemleri gerekecektir.
