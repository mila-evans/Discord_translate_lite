from flask import Flask
import threading
import discord
from discord.ext import commands
import requests
from langdetect import detect
from dotenv import load_dotenv
import os
import json

# .env ファイルを読み込む
load_dotenv()

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

# Discord Bot 設定
Discord_Token = os.getenv("DISCORD_TOKEN")
DeepL_Token = os.getenv("DEEPL_TOKEN")
DeepL_API_URL = "https://api-free.deepl.com/v2/translate"

Intents = discord.Intents.default()
Intents.message_content = True

# commands.Bot を使用
bot = commands.Bot(command_prefix="/", intents=Intents)

# 翻訳チャンネル情報の保存ファイル
TRANSLATION_FILE = "translation_channels.json"

# 翻訳チャンネルを読み込む
def load_translation_channels():
    try:
        with open(TRANSLATION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# 翻訳チャンネルを保存
def save_translation_channels(data):
    with open(TRANSLATION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# 翻訳チャンネルリスト（ギルドごと）
translation_channels = load_translation_channels()

# 言語判別関数
def detect_language(text):
    lang = detect(text)
    lang_map = {
        "en": "EN",
        "ja": "JA",
        "ko": "KO",
        "fr": "FR",
        "de": "DE",
    }
    return lang_map.get(lang, "EN")

# 起動時動作
@bot.event
async def on_ready():
    print("起動しました")
    print("登録されている翻訳チャンネル:", translation_channels)
    
    # スラッシュコマンドを同期
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} 個のコマンドを同期しました！")
    except Exception as e:
        print(f"⚠️ コマンドの同期に失敗しました: {e}")

# スラッシュコマンドで翻訳チャンネルを追加
@bot.tree.command(name="add_translation_channel")
async def add_translation_channel(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    channel_id = str(interaction.channel.id)

    if guild_id not in translation_channels:
        translation_channels[guild_id] = []

    if channel_id in translation_channels[guild_id]:
        await interaction.response.send_message("このチャンネルはすでに翻訳対象になっています！")
    else:
        translation_channels[guild_id].append(channel_id)
        save_translation_channels(translation_channels)
        await interaction.response.send_message("✅ このチャンネルを翻訳対象に追加しました！")

# スラッシュコマンドで翻訳チャンネルを削除
@bot.tree.command(name="remove_translation_channel")
async def remove_translation_channel(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    channel_id = str(interaction.channel.id)

    if guild_id in translation_channels and channel_id in translation_channels[guild_id]:
        translation_channels[guild_id].remove(channel_id)
        if not translation_channels[guild_id]:  # 空になったら削除
            del translation_channels[guild_id]
        save_translation_channels(translation_channels)
        await interaction.response.send_message("✅ このチャンネルを翻訳対象から削除しました！")
    else:
        await interaction.response.send_message("このチャンネルは翻訳対象ではありません！")

# スラッシュコマンドで登録されている翻訳チャンネル一覧を表示
@bot.tree.command(name="list_translation_channels")
async def list_translation_channels(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)

    if guild_id not in translation_channels or not translation_channels[guild_id]:
        await interaction.response.send_message("登録されている翻訳チャンネルはありません！")
        return

    msg = "\n".join([f"<#{ch_id}>" for ch_id in translation_channels[guild_id]])
    await interaction.response.send_message(f"📜 登録されている翻訳チャンネル:\n{msg}")
    
# メッセージ受信時動作
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    guild_id = str(message.guild.id)
    channel_id = str(message.channel.id)

    # 翻訳対象のチャンネルでない場合は無視
    if guild_id not in translation_channels or channel_id not in translation_channels[guild_id]:
        return

    # 言語判定
    source_lang = detect_language(message.content)
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
        await message.channel.send(f"📝 翻訳結果:\n{translated_text}")
    else:
        await message.channel.send(f"❌ 翻訳に失敗しました（{response.status_code}）")

# Bot を起動
bot.run(Discord_Token)
