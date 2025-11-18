import discord
import os
import aiohttp
import feedparser
import hashlib
from bs4 import BeautifulSoup
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone

# ────── Fix privileged intent warning ──────
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
seen = set()

# ────── Skinflint checker ──────
async def check_skinflint(session):
    try:
        async with session.get(
            "https://skinflint.co.uk/amd-ryzen-7-9800x3d-a3336051.html",
            timeout=15
        ) as r:
            if r.status != 200:
                return None
            soup = BeautifulSoup(await r.text(), "html.parser")
            for item in soup.select("div.p")[:5]:
                price_str = item.select_one("span.price").get_text(strip=True).replace("£", "").replace(",", "")
                price = float(price_str)
                if price < 449:  # change here if you want £439 etc.
                    shop = item.select_one("span.vendor").get_text(strip=True)
                    link = "https://skinflint.co.uk" + item.select_one("a.p-name")["href"]
                    key = hashlib.md5(link.encode()).hexdigest()
                    if key not in seen:
                        seen.add(key)
                        return f"£{price:.2f} → {shop}\n{link}"
    except:
        pass
    return None

# ────── HotUKDeals checker ──────
async def check_hukd():
    try:
        feed = feedparser.parse("https://www.hotukdeals.com/tag/amd-ryzen/rss")
        for e in feed.entries[:10]:
            if "9800X3D" in e.title.upper() and e.link not in seen:
                seen.add(e.link)
                return f"HUKD DEAL!\n{e.title}\n{e.link}"
    except:
        pass
    return None

# ────── Main scan function (awaits everything properly) ──────
async def scan_deals():
    channel = bot.get_channel(int(os.getenv("CHANNEL_ID")))
    if not channel:
        return

    async with aiohttp.ClientSession() as session:
        alerts = []

        skinflint_result = await check_skinflint(session)
        if skinflint_result:
            alerts.append(skinflint_result)

        hukd_result = await check_hukd()
        if hukd_result:
            alerts.append(hukd_result)

        for text in alerts:
            embed = discord.Embed(
                description=text,
                color=0xff0000,
                timestamp=datetime.now(timezone.utc)   # ← fixes utcnow() deprecation
            )
            embed.set_author(name="9800X3D UNDER £449!", icon_url="https://i.imgur.com/2JLcV4A.png")
            await channel.send("@everyone", embed=embed)

# ────── Bot ready ──────
@bot.event
async def on_ready():
    print(f"Bot {bot.user} is LIVE – hunting 9800X3D 24/7")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(scan_deals, "interval", minutes=3)   # ← correct function name
    scheduler.start()
    await scan_deals()   # first immediate scan

# ────── Start the bot ──────
bot.run(os.getenv("TOKEN"))
