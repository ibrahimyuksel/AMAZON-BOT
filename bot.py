diff --git a/bot.py b/bot.py
new file mode 100644
index 0000000000000000000000000000000000000000..6466a5a413df6a9a0a304e1eb4409fd0d6eb71bd
--- /dev/null
+++ b/bot.py
@@ -0,0 +1,246 @@
+import logging
+import os
+import random
+import re
+import time
+from dataclasses import dataclass
+from typing import Optional
+from urllib.parse import quote_plus
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
+AMAZON_URL_RE = re.compile(r"https?://(?:www\.)?amazon\.[^\s]+", re.IGNORECASE)
+
+USER_AGENTS = [
+    (
+        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
+        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
+    ),
+    (
+        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
+        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
+    ),
+    (
+        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
+        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
+    ),
+]
+
+PRICE_SELECTORS = [
+    "#priceblock_dealprice",
+    "#priceblock_ourprice",
+    "#priceblock_saleprice",
+    "#corePrice_feature_div .a-offscreen",
+    ".a-price .a-offscreen",
+]
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
+def _contains_antibot_page(html: str) -> bool:
+    html_lower = html.lower()
+    anti_bot_markers = [
+        "captcha",
+        "enter the characters you see below",
+        "sorry, we just need to make sure you're not a robot",
+        "automated access",
+    ]
+    return any(marker in html_lower for marker in anti_bot_markers)
+
+
+def _parse_product_info(html: str, url: str) -> ProductInfo:
+    soup = BeautifulSoup(html, "html.parser")
+
+    title_tag = soup.select_one("#productTitle")
+    title = title_tag.get_text(strip=True) if title_tag else "Başlık bulunamadı"
+
+    price = None
+    for selector in PRICE_SELECTORS:
+        node = soup.select_one(selector)
+        if node:
+            maybe_price = node.get_text(strip=True)
+            if maybe_price:
+                price = maybe_price
+                break
+
+    if not price:
+        raise AmazonScrapeError(
+            "Fiyat bulunamadı. Ürün stokta olmayabilir ya da sayfa farklı bir şablon kullanıyor olabilir."
+        )
+
+    return ProductInfo(title=title, price=price, url=url)
+
+
+def _get_with_retry(url: str, timeout: int = 20, max_attempts: int = 3) -> requests.Response:
+    last_exception: Optional[Exception] = None
+
+    for attempt in range(1, max_attempts + 1):
+        headers = {
+            "User-Agent": random.choice(USER_AGENTS),
+            "Accept-Language": "en-US,en;q=0.9,tr-TR;q=0.8,tr;q=0.7",
+            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
+            "Connection": "keep-alive",
+        }
+
+        try:
+            response = requests.get(url, headers=headers, timeout=timeout)
+            if response.status_code == 200:
+                return response
+
+            logger.warning("İstek başarısız oldu (deneme=%s, status=%s)", attempt, response.status_code)
+        except requests.RequestException as exc:
+            last_exception = exc
+            logger.warning("İstek hatası (deneme=%s): %s", attempt, exc)
+
+        if attempt < max_attempts:
+            time.sleep(1.5 * attempt)
+
+    if last_exception:
+        raise AmazonScrapeError("Amazon sayfası alınamadı.") from last_exception
+
+    raise AmazonScrapeError("Amazon sayfası alınamadı.")
+
+
+def _scrape_via_scrapingbee(url: str) -> Optional[ProductInfo]:
+    api_key = os.getenv("SCRAPINGBEE_API_KEY")
+    if not api_key:
+        return None
+
+    logger.info("Direct scraping engellendi; ScrapingBee fallback denemesi yapılıyor.")
+    endpoint = (
+        "https://app.scrapingbee.com/api/v1/"
+        f"?api_key={quote_plus(api_key)}&url={quote_plus(url)}&render_js=false&premium_proxy=true"
+    )
+
+    try:
+        response = requests.get(endpoint, timeout=30)
+        response.raise_for_status()
+    except requests.RequestException:
+        return None
+
+    if _contains_antibot_page(response.text):
+        return None
+
+    try:
+        return _parse_product_info(response.text, url)
+    except AmazonScrapeError:
+        return None
+
+
+def scrape_amazon_price(url: str) -> ProductInfo:
+    response = _get_with_retry(url=url)
+
+    if _contains_antibot_page(response.text):
+        fallback_result = _scrape_via_scrapingbee(url)
+        if fallback_result:
+            return fallback_result
+
+        raise AmazonScrapeError(
+            "Amazon anti-bot sayfası tespit edildi. Çözüm: SCRAPINGBEE_API_KEY ekleyin "
+            "veya resmi Amazon Product Advertising API kullanın."
+        )
+
+    return _parse_product_info(response.text, url)
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
+        "/price <amazon_urun_linki>\n"
+        "/anti_bot"
+    )
+
+
+async def anti_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
+    if update.message is None:
+        return
+
+    await update.message.reply_text(
+        "Anti-bot için öneriler:\n"
+        "1) En sağlam yöntem: Amazon Product Advertising API kullanmak.\n"
+        "2) Proxy scraping servisi fallback: SCRAPINGBEE_API_KEY ekleyin.\n"
+        "3) İstekleri seyrek gönderin, cache kullanın (aynı linki kısa sürede tekrar çekmeyin).\n"
+        "4) CAPTCHA dönen sayfaları zorlamayın; TOS ihlallerinden kaçının."
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
+    app.add_handler(CommandHandler("anti_bot", anti_bot))
+    app.add_handler(CommandHandler("price", price))
+
+    logger.info("Bot başlatılıyor...")
+    app.run_polling(drop_pending_updates=True)
+
+
+if __name__ == "__main__":
+    main()
