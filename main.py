import discord
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup
import feedparser
import os
import hashlib
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

seen_deals = set()
PRICE_THRESHOLD = int(os.getenv("PRICE_THRESHOLD", "449"))  # Change in Render env vars

async def check_skinflint(session):
    url = "https://skinflint.co.uk/amd-ryzen-7-9800x3d-a3336051.html"
    async with session.get(url, timeout=15) as resp:
        if resp.status != 200: return None
        soup = BeautifulSoup(await resp.text(), "html.parser")
        for item in soup.select("div.p")[:5]:
            price_tag = item.select_one("span.price")
            if not price_tag: continue
            price = price_tag.text.strip().replace("£", "").replace(",", "")
            if not price.replace(".", "").isdigit(): continue
            price = float(price)
            if price > PRICE_THRESHOLD: continue
            
            shop = item.select_one("span.vendor").text.strip()
            link = "https://skinflint.co.uk" + item.select_one("a.p-name")["href"]
            key = hashlib.md5(f"{price}{shop}{link}".encode()).hexdigest()
            if key not in seen_deals:
                seen_deals.add(key)
                return f"£{price:.2f} → {shop}\n{link}"
    return None

async def check_hukd():
    feed = feedparser.parse("https://www.hotukdeals.com/tag/amd-ryzen/rss")
    for entry in feed.entries[:10]:
        if "9800X3D" in entry.title.upper() and entry.link not in seen_deals:
            seen_deals.add(entry.link)
            return f"HUKD ALERT\n{entry.title}\n{entry.link}"
    return None

async def scan():
    channel_id = int(os.getenv("CHANNEL_ID"))
    channel = bot.get_channel(channel_id)
    if not channel: return

    async with aiohttp.ClientSession() as session:
        alerts = []
        skin = await check_skinflint(session)
        if skin: alerts.append(skin)
        hukd = check_hukd()
        if hukd: alerts.append(hukd)

        for alert in alerts:
            embed = discord.Embed(description=alert, color=0xff0000, timestamp=datetime.utcnow())
            embed.set_author(name="9800X3D UNDER £449!", icon_url="https://i.imgur.com/2JLcV4A.png")
            await channel.send("@everyone", embed=embed)

@bot.event
async def on_ready():
    print(f"{bot.user} is LIVE – hunting 9800X3D deals 24/7")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(scan, "interval", minutes=3)
    scheduler.start()
    await scan()

bot.run(os.getenv("DISCORD_TOKEN"))
