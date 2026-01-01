#!/usr/bin/env python3
"""Quick test to verify Discord webhook is working."""

import os
from dotenv import load_dotenv

load_dotenv()

webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
print(f"Discord Webhook URL: {webhook_url[:50]}...")

try:
    from discord_webhook import DiscordWebhook, DiscordEmbed
    
    webhook = DiscordWebhook(url=webhook_url, rate_limit_retry=True)
    
    embed = DiscordEmbed(
        title="🧪 Test Notification",
        description="If you see this, Discord notifications are working!",
        color=0x00ff00
    )
    embed.add_embed_field(name="Status", value="✅ Connected", inline=True)
    embed.add_embed_field(name="Bot", value="Copy Trading Bot", inline=True)
    embed.add_embed_field(
        name="Info", 
        value="You'll receive alerts when tracked whales make NEW trades.\n\n"
              "Currently tracking 5 whales (archaic, Car, nicoco89, JJo, Anjun).\n\n"
              "No alerts yet = No new trades detected.", 
        inline=False
    )
    embed.set_footer(text="Predictions Market Arbitrage Bot")
    
    webhook.add_embed(embed)
    response = webhook.execute()
    
    print(f"Response status: {response.status_code}")
    if response.status_code in [200, 204]:
        print("✅ Discord notification sent successfully!")
        print("Check your Discord channel now.")
    else:
        print(f"❌ Failed: {response.text}")
        
except ImportError:
    print("❌ discord-webhook not installed. Run: pip install discord-webhook")
except Exception as e:
    print(f"❌ Error: {e}")

