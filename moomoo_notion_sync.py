"""
Moomoo → Notion Daily P&L Sync
Runs once at market close to sync your positions to a Notion database.

Requirements:
    pip install moomoo-api notion-client python-dotenv

Setup:
    1. Create a .env file in the same folder (see README section below)
    2. Run Moomoo OpenD desktop app before executing this script
    3. Schedule this script via Task Scheduler (Windows) or cron (Mac/Linux)
"""

import os
import datetime
from dotenv import load_dotenv
from moomoo import OpenQuoteContext, OpenSecTradeContext, TrdMarket, RET_OK
from notion_client import Client

# ── Load secrets from .env ───────────────────────────────────────────────────
load_dotenv()

NOTION_TOKEN      = os.getenv("NOTION_TOKEN")       # your Notion integration token
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID") # your Notion database ID
MOOMOO_HOST         = os.getenv("MOOMOO_HOST", "127.0.0.1")
MOOMOO_PORT         = int(os.getenv("MOOMOO_PORT", "11111"))
MOOMOO_PWD_UNLOCK   = os.getenv("MOOMOO_PWD_UNLOCK", "")  # trading unlock password
MOOMOO_MARKET       = os.getenv("MOOMOO_MARKET", "US")    # US or HK


# ── Pull positions from Moomoo (via Moomoo OpenD) ──────────────────────────────
def get_positions():
    # notion = Client(auth=NOTION_TOKEN)
    # print(dir(notion))
    
    """
    Returns a list of dicts with position data from Moomoo.
    Make sure Moomoo OpenD is running on your machine first.
    """
    market_map = {
        "US": TrdMarket.US,
        "HK": TrdMarket.HK,
    }
    trd_market = market_map.get(MOOMOO_MARKET.upper(), TrdMarket.US)

    trd_ctx = OpenSecTradeContext(
        filter_trdmarket=trd_market,
        host=MOOMOO_HOST,
        port=MOOMOO_PORT
    )

    # Unlock trading context (needed to read positions)
    if MOOMOO_PWD_UNLOCK:
        ret, data = trd_ctx.unlock_trade(MOOMOO_PWD_UNLOCK)
        if ret != RET_OK:
            print(f"[WARN] Trade unlock failed: {data} — continuing anyway")

    ret, data = trd_ctx.position_list_query()
    trd_ctx.close()

    if ret != RET_OK:
        raise RuntimeError(f"Failed to fetch positions: {data}")

    positions = []
    for _, row in data.iterrows():
        ticker     = str(row.get("code", "")).split(".")[-1]  # strip exchange prefix
        shares     = float(row.get("qty", 0))
        avg_cost   = float(row.get("cost_price", 0))
        cur_price  = float(row.get("last_price", 0) or row.get("market_val", 0) / shares if shares else 0)
        pl_val     = float(row.get("pl_val", 0))          # Total P&L $
        pl_ratio   = float(row.get("pl_ratio", 0)) * 100  # Total P&L % (moomoo gives 0-1)
        today_pl   = float(row.get("today_pl_val", 0))    # Daily P&L $

        positions.append({
            "ticker":    ticker,
            "shares":    shares,
            "avg_cost":  avg_cost,
            "cur_price": cur_price,
            "daily_pl":  today_pl,
            "total_pl":  pl_val,
            "total_pct": pl_ratio,
        })

    return positions


# ── Notion helpers ────────────────────────────────────────────────────────────
def get_notion_client():
    return Client(auth=NOTION_TOKEN)


def get_existing_pages(notion):
    """
    Returns a dict of { ticker: page_id } for all rows already in the database.
    Used to decide whether to create or update.
    """
    
    results = notion.databases.update(database_id=NOTION_DATABASE_ID).get("results", [])
    pages = {}
    for page in results:
        props = page.get("properties", {})
        title_prop = props.get("Ticker", {}).get("title", [])
        if title_prop:
            ticker = title_prop[0]["text"]["content"]
            pages[ticker] = page["id"]
    return pages


def build_properties(pos, sync_date):
    """
    Maps a position dict to Notion page properties.
    Must match the property names/types in your Notion database exactly.
    """
    return {
        "Ticker": {
            "title": [{"text": {"content": pos["ticker"]}}]
        },
        "Shares Held": {
            "number": pos["shares"]
        },
        "Avg Cost": {
            "number": round(pos["avg_cost"], 4)
        },
        "Current Price": {
            "number": round(pos["cur_price"], 4)
        },
        "Daily P&L ($)": {
            "number": round(pos["daily_pl"], 2)
        },
        "Total P&L ($)": {
            "number": round(pos["total_pl"], 2)
        },
        "Total P&L (%)": {
            "number": round(pos["total_pct"], 2)
        },
        "Last Synced": {
            "date": {"start": sync_date.isoformat()}
        },
    }


def upsert_position(notion, pos, existing_pages, sync_date):
    """
    Creates a new Notion page for a position, or updates it if it already exists.
    """
    props = build_properties(pos, sync_date)
    ticker = pos["ticker"]

    if ticker in existing_pages:
        notion.pages.update(page_id=existing_pages[ticker], properties=props)
        print(f"  ✔ Updated  {ticker}")
    else:
        notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties=props
        )
        print(f"  ✔ Created  {ticker}")


def remove_closed_positions(notion, positions, existing_pages):
    """
    Archives Notion rows for tickers no longer in your portfolio.
    """
    active_tickers = {p["ticker"] for p in positions}
    for ticker, page_id in existing_pages.items():
        if ticker not in active_tickers:
            notion.pages.update(page_id=page_id, archived=True)
            print(f"  ✘ Archived {ticker} (position closed)")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    sync_date = datetime.datetime.now()
    print(f"\n{'='*50}")
    print(f"  Moomoo → Notion Sync  |  {sync_date.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    print("\n[1/3] Fetching positions from Moomoo...")
    positions = get_positions()
    print(f"      Found {len(positions)} open position(s)")

    print("\n[2/3] Reading existing Notion rows...")
    notion = get_notion_client()
    existing_pages = get_existing_pages(notion)
    print(f"      Found {len(existing_pages)} existing row(s)")

    print("\n[3/3] Syncing to Notion...")
    for pos in positions:
        upsert_position(notion, pos, existing_pages, sync_date)

    remove_closed_positions(notion, positions, existing_pages)

    print(f"\n✅ Sync complete — {len(positions)} position(s) updated in Notion\n")


if __name__ == "__main__":
    main()
