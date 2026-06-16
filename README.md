# Moomoo → Notion Daily P&L Sync — Setup Guide

Syncs your Moomoo positions to a Notion database every day at market close. 100% free.

---

## What you need
- Python 3.8+
- [Futu OpenD](https://www.futunn.com/download/OpenAPI) (free desktop app by Moomoo/Futu)
- A Notion account (free tier is fine)

---

## Step 1 — Install Python dependencies

```bash/cmd
pip install futu-api notion-client python-dotenv
```

---

## Step 2 — Set up Futu OpenD

1. Download and install **Moomoo OpenD** from https://www.moomoo.com/download/OpenAPI
2. Open it and log in with your Moomoo account
3. Leave it running in the background whenever you want to sync

---

## Step 3 — Create your Notion database

1. In Notion, create a new **full-page database** (Table view)
2. Add these columns with exactly these names and types:

| Property Name   | Type   |
|-----------------|--------|
| Ticker          | Title  |
| Shares Held     | Number |
| Avg Cost        | Number |
| Current Price   | Number |
| Daily P&L ($)   | Number |
| Total P&L ($)   | Number |
| Total P&L (%)   | Number |
| Last Synced     | Date   |

3. For number columns, set the format:
   - **Avg Cost / Current Price** → Number (4 decimals)
   - **Daily P&L ($) / Total P&L ($)** → Dollar
   - **Total P&L (%)** → Percent (or Number with a % suffix)

---

## Step 4 — Create a Notion Integration

1. Go to https://www.notion.so/my-integrations
2. Click **New Integration** → give it a name (e.g. "Moomoo Sync")
3. Copy the **Internal Integration Token** (starts with `ntn_...`)
4. Back in your Notion database → click **...** (top right) → **Connections** → Type the Integration Name → select your integration

---

## Step 5 — Configure your .env file

1. Rename `.env.example` to `.env`
2. Fill in:
   - `NOTION_TOKEN` — your integration token from Step 4
   - `NOTION_DATABASE_ID` — copy from your database URL:
     `https://notion.so/workspace/<THIS_PART>?v=...`
   - `FUTU_PWD_UNLOCK` — your Moomoo trading PIN
   - `FUTU_MARKET` — `US` or `HK`

---

## Step 6 — Test it

Make sure Futu OpenD is running, then:

```bash
python moomoo_notion_sync.py
```

You should see output like:
```
==================================================
  Moomoo → Notion Sync  |  2026-06-16 16:05:00
==================================================

[1/3] Fetching positions from Moomoo...
      Found 5 open position(s)

[2/3] Reading existing Notion rows...
      Found 0 existing row(s)

[3/3] Syncing to Notion...
  ✔ Created  AAPL
  ✔ Created  TSLA
  ...

✅ Sync complete — 5 position(s) updated in Notion
```

---

## Step 7 — Schedule daily at market close

### Windows (Task Scheduler)
1. Open **Task Scheduler** → Create Basic Task
2. Name: `Moomoo Notion Sync`
3. Trigger: **Daily** at **4:05 PM** (just after US market close)
4. Action: **Start a program**
   - Program: `python`
   - Arguments: `C:\path\to\moomoo_notion_sync.py`
   - Start in: `C:\path\to\your\folder\`

### Mac/Linux (cron)
```bash
crontab -e
```
Add this line (runs at 4:05 PM Mon–Fri):
```
5 16 * * 1-5 /usr/bin/python3 /path/to/moomoo_notion_sync.py >> /path/to/sync.log 2>&1
```

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `Connection refused` on Futu | Make sure Futu OpenD is running |
| `401 Unauthorized` on Notion | Check your `NOTION_TOKEN` in `.env` |
| `object_not_found` on Notion | Check your `NOTION_DATABASE_ID` and that the integration is connected to the DB |
| Positions show 0 values | Try unlocking trade in OpenD settings first |

---

## How sync works

- **New ticker** → creates a new row in Notion
- **Existing ticker** → updates the row in place
- **Closed position** → archives the row automatically