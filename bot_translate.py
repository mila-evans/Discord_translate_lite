from flask import Flask
import threading
import discord
import requests
from langdetect import detect
import os

# Flask アプリケーション
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

# Flask サーバーをバックグラウンドで実行
def run():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

server_thread = threading.Thread(target=run)
server_thread.start()

# Discord Bot
Discord_Token = os.getenv("DISCORD_TOKEN")
Discord_channel_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

Intents = discord.Intents.default()
Intents.message_content = True

client = discord.Client(intents=Intents)

# 言語判別関数
def language(text):
    lang = detect(text)
    lang_map = {
        "en": "EN",  # 英語
        "ja": "JA",  # 日本語
        "ko": "KO",  # 韓国語
        "fr": "FR",  # フランス語
        "de": "DE",  # ドイツ語
    }
    return lang_map.get(lang, "EN")  # 対応していない言語の場合は英語

# 起動時動作
@client.event
async def on_ready():
    print("起動しました")

# メッセージ受信時動作
@client.event
async def on_message(message):
    if message.channel.id != Discord_channel_ID:
        return
    if message.author == client.user:
        return
    if message.content.startswith("おやすみ"):
        await message.channel.send("おやすみ！また明日！")
        await client.close()
        exit()

    DeepL_Token = os.getenv("DEEPL_TOKEN")
    DeepL_API_URL = "https://api-free.deepl.com/v2/translate"
    source_lang = language(message.content)

    target_lang = "KO" if source_lang == "JA" else "JA"
    params = {
        "auth_key": DeepL_Token,
        "text": message.content,
        "source_lang": source_lang,
        "target_lang": target_lang
    }

    response = requests.post(DeepL_API_URL, data=params)

    if response.status_code == 200:
        response_json = response.json()
        translated_text = response_json["translations"][0]["text"]
        await message.channel.send(translated_text)
    else:
        await message.channel.send(f"Error {response.status_code}: {response.text}")

client.run(Discord_Token)
