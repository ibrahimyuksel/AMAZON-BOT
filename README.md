# Amazon Price Telegram Bot

Telegram üzerinden Amazon ürün fiyatı kontrol etmek için basit bir bot.

## Kurulum

1. Python 3.10+ kurulu olmalı.
2. Bağımlılıkları yükleyin:

```bash
pip install -r requirements.txt
```

3. `.env` dosyası oluşturun:

```bash
cp .env.example .env
```

4. `.env` içindeki `TELEGRAM_BOT_TOKEN` değerini BotFather'dan aldığınız token ile doldurun.

## Çalıştırma

```bash
python bot.py
```

## Kullanım

- `/start`
- `/price <amazon_linki>`

Örnek:

```text
/price https://www.amazon.com/dp/B0C2S6V77M
```

## Notlar

- Amazon anti-bot koruması nedeniyle bazı sayfalarda fiyat alınamayabilir.
- Bölgesel Amazon alan adları (`amazon.com`, `amazon.de`, `amazon.com.tr`) desteklenir.
