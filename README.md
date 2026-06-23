# News Digest Bot

A scheduled bot that scrapes RSS feeds (Hacker News, arXiv, GitHub Trending, security/fintech blogs),
filters articles by keyword, and sends a formatted digest to Telegram every 48 hours via GitHub Actions.

No paid APIs, no AI summarization — just fetch, filter, format, and send.

## How it works

1. `digest.py` fetches all sources in `SOURCES` using `feedparser`.
2. Entries are filtered by keyword match (title or summary) and deduplicated by URL.
3. Up to 10 new articles (not previously sent) are formatted into a Spanish-language Telegram message.
4. The message is sent via the Telegram Bot API (`sendMessage`, `MarkdownV2`).
5. Sent URLs are recorded in `sent_urls.json` so they're never sent again.

## 1. Create a Telegram bot with @BotFather

1. Open Telegram and search for **@BotFather**.
2. Send `/newbot` and follow the prompts (choose a name and a username ending in `bot`).
3. BotFather will reply with a token that looks like:
   `123456789:AAExampleTokenStringHere`
   This is your `TELEGRAM_BOT_TOKEN`. Keep it secret.

## 2. Get your chat ID

1. Send any message to your new bot (open it in Telegram and click "Start" / send `/start` or any text).
2. In your browser, visit:
   `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Look for the `"chat":{"id": ...}` field in the JSON response. That number is your `TELEGRAM_CHAT_ID`.
   - If you want the digest sent to a group instead of a DM, add the bot to the group, send a message
     in the group, and use the same `getUpdates` call — the chat ID for groups is usually negative.

## 3. Add secrets to GitHub

In your repository on GitHub:

1. Go to **Settings → Secrets and variables → Actions → New repository secret**.
2. Add:
   - `TELEGRAM_BOT_TOKEN` — the token from BotFather.
   - `TELEGRAM_CHAT_ID` — the chat ID from step 2.

## 4. Enable the workflow

The workflow file is at `.github/workflows/digest.yml`. It:

- Runs automatically every 2 days at 08:00 UTC (`cron: '0 8 */2 * *'`).
- Can be triggered manually from the **Actions** tab via `workflow_dispatch`.
- Persists `sent_urls.json` between runs (caches it and commits it back to the repo)
  so articles already sent are never repeated.

Push this repository to GitHub and the workflow will appear under the **Actions** tab.
You can trigger it manually with **Run workflow** to test it immediately.

## 5. Run it locally (optional)

```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN="your-token"
export TELEGRAM_CHAT_ID="your-chat-id"
python digest.py
```

## Customizing

- **Sources**: edit the `SOURCES` list in `digest.py`.
- **Keywords**: edit the `KEYWORDS` list in `digest.py`.
- **Max articles per run**: change `MAX_ARTICLES` in `digest.py`.
- **Schedule**: edit the `cron` expression in `.github/workflows/digest.yml`.
