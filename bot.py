diff --git a/bot.py b/bot.py
new file mode 100644
index 0000000000000000000000000000000000000000..7b1065ae5524532990af3e04a0bb228bf6a8eae0
--- /dev/null
+++ b/bot.py
@@ -0,0 +1,144 @@
+import logging
+import os
+import re
+from dataclasses import dataclass
+from typing import Optional
+
+import requests
+from bs4 import BeautifulSoup
+from dotenv import load_dotenv
+from telegram import Update
+from telegram.ext import Application, CommandHandler, ContextTypes
+
+
+load_dotenv()
+
+logging.basicConfig(
+    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
+    level=logging.INFO,
+)
+logger = logging.getLogger("amazon_price_bot")
+
+
+AMAZON_URL_RE = re.compile(r"https?://(?:www\\.)?amazon\\.[^\s]+", re.IGNORECASE)
+
+
+@dataclass
+class ProductInfo:
+    title: str
+    price: str
+    url: str
+
+
+class AmazonScrapeError(Exception):
+    pass
+
+
+def extract_amazon_url(text: str) -> Optional[str]:
+    match = AMAZON_URL_RE.search(text)
+    return match.group(0) if match else None
+
+
+def scrape_amazon_price(url: str) -> ProductInfo:
+    headers = {
+        "User-Agent": (
+            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
+            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
+        ),
+        "Accept-Language": "en-US,en;q=0.9,tr-TR;q=0.8,tr;q=0.7",
+    }
+
+    try:
+        response = requests.get(url, headers=headers, timeout=20)
+        response.raise_for_status()
+    except requests.RequestException as exc:
+        raise AmazonScrapeError("Amazon sayfası alınamadı.") from exc
+
+    soup = BeautifulSoup(response.text, "html.parser")
+
+    title_tag = soup.select_one("#productTitle")
+    title = title_tag.get_text(strip=True) if title_tag else "Başlık bulunamadı"
+
+    candidate_selectors = [
+        "#priceblock_dealprice",
+        "#priceblock_ourprice",
+        "#priceblock_saleprice",
+        "#corePrice_feature_div .a-offscreen",
+        ".a-price .a-offscreen",
+    ]
+
+    price = None
+    for selector in candidate_selectors:
+        node = soup.select_one(selector)
+        if node:
+            maybe_price = node.get_text(strip=True)
+            if maybe_price:
+                price = maybe_price
+                break
+
+    if not price:
+        raise AmazonScrapeError(
+            "Fiyat bulunamadı. Sayfa bot koruması gösteriyor olabilir veya ürün stokta olmayabilir."
+        )
+
+    return ProductInfo(title=title, price=price, url=url)
+
+
+async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
+    if update.message is None:
+        return
+
+    await update.message.reply_text(
+        "Merhaba 👋\n"
+        "Amazon fiyat kontrol botuna hoş geldin.\n\n"
+        "Kullanım:\n"
+        "/price <amazon_urun_linki>"
+    )
+
+
+async def price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
+    if update.message is None:
+        return
+
+    text = " ".join(context.args).strip() if context.args else update.message.text or ""
+    url = extract_amazon_url(text)
+
+    if not url:
+        await update.message.reply_text(
+            "Geçerli bir Amazon linki bulunamadı.\n"
+            "Örnek: /price https://www.amazon.com/dp/B0..."
+        )
+        return
+
+    await update.message.reply_text("Fiyat kontrol ediliyor, lütfen bekleyin...")
+
+    try:
+        product = scrape_amazon_price(url)
+    except AmazonScrapeError as exc:
+        await update.message.reply_text(f"❌ {exc}")
+        return
+
+    await update.message.reply_text(
+        f"🛍️ *{product.title}*\n"
+        f"💰 *Fiyat:* {product.price}\n"
+        f"🔗 {product.url}",
+        parse_mode="Markdown",
+        disable_web_page_preview=True,
+    )
+
+
+def main() -> None:
+    token = os.getenv("TELEGRAM_BOT_TOKEN")
+    if not token:
+        raise RuntimeError("TELEGRAM_BOT_TOKEN tanımlı değil. .env dosyasını kontrol edin.")
+
+    app = Application.builder().token(token).build()
+    app.add_handler(CommandHandler("start", start))
+    app.add_handler(CommandHandler("price", price))
+
+    logger.info("Bot başlatılıyor...")
+    app.run_polling(drop_pending_updates=True)
+
+
+if __name__ == "__main__":
+    main()
