# Amazon Price Telegram Bot

Telegram üzerinden Amazon ürün fiyatı kontrol etmek için bot.

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

4. `.env` içinde:
   - `TELEGRAM_BOT_TOKEN` (zorunlu)
   - `SCRAPINGBEE_API_KEY` (opsiyonel ama anti-bot fallback için önerilir)

## Çalıştırma

```bash
python bot.py
```

## Kullanım

- `/start`
- `/price <amazon_linki>`
- `/anti_bot` (anti-bot önerileri)

Örnek:

```text
/price https://www.amazon.com/dp/B0C2S6V77M
```

## Anti-bot notları

Amazon anti-bot koruması nedeniyle doğrudan HTML scraping her zaman stabil değildir.

Bu repoda şu iyileştirmeler var:

- User-Agent rotasyonu
- Retry + bekleme
- CAPTCHA/anti-bot sayfası tespiti
- Opsiyonel ScrapingBee fallback (`SCRAPINGBEE_API_KEY` varsa)

Daha sağlam ve uzun vadeli çözüm için resmi **Amazon Product Advertising API** tercih edilmelidir.
