from flask import Flask
import threading
import discord
from discord.ext import commands
import requests
from langdetect import detect
import os
import json

# Flask アプリケーション
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

server_thread = threading.Thread(target=run)
server_thread.start()

Discord_Token = os.getenv("DISCORD_TOKEN")
DeepL_Token = os.getenv("DEEPL_TOKEN")
DeepL_API_URL = "https://api-free.deepl.com/v2/translate"

Intents = discord.Intents.default()
Intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=Intents)

# 翻訳設定の保存ファイル
TRANSLATION_SETTINGS_FILE = "translation_settings.json"

# 翻訳設定を読み込む
def load_translation_settings():
    try:
        with open(TRANSLATION_SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# 翻訳設定を保存
def save_translation_settings(data):
    with open(TRANSLATION_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# **翻訳設定の読み込みを追加**
translation_settings = load_translation_settings()

# 翻訳チャンネル情報の保存ファイル
TRANSLATION_FILE = "translation_channels.json"

def load_translation_channels():
    try:
        with open(TRANSLATION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_translation_channels(data):
    with open(TRANSLATION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

translation_channels = load_translation_channels()

from langdetect import detect_langs

def detect_language(text):
    lang_probs = detect_langs(text)  # 言語の信頼度リスト取得
    lang_map = {
        "en": "EN",
        "ja": "JA",
        "zh-cn": "JA",  # 誤判定を日本語として処理
        "zh-tw": "JA",  # 繁体字も考慮
        "ko": "KO",
        "fr": "FR",
    }

    # 一番信頼度の高い言語を取得
    detected_lang = lang_probs[0].lang

    # 中国語と判定されても、日本語の可能性が高ければ JA にする
    if detected_lang.startswith("zh"):
        # もし他の言語の確率が高ければそちらを優先
        for lang in lang_probs:
            if lang.lang == "ja" and lang.prob > 0.3:  # 30%以上の確率で日本語なら日本語とみなす
                return "JA"

    return lang_map.get(detected_lang, "EN")

@bot.event
async def on_ready():
    print("起動しました")
    print("現在の翻訳設定:", translation_settings)
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

@bot.tree.command(name="set_translation_language")
async def set_translation_language(interaction: discord.Interaction, target_lang: str):
    guild_id = str(interaction.guild.id)
    
    supported_languages = ["EN", "KO", "FR", "ZH-HANS"]
    if target_lang.upper() not in supported_languages:
        await interaction.response.send_message("❌ 対応していない言語です！ (対応言語: EN, KO, FR, ZH-HANS)")
        return
    
    translation_settings[guild_id] = target_lang.upper()
    save_translation_settings(translation_settings)
    await interaction.response.send_message(f"✅ 翻訳言語を `{target_lang.upper()}` に設定しました！")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    guild_id = str(message.guild.id)
    channel_id = str(message.channel.id)

    if guild_id not in translation_channels or channel_id not in translation_channels[guild_id]:
        return

    source_lang = detect_language(message.content)
    target_lang = translation_settings.get(guild_id, "JA")
    
    # 日本語以外のメッセージは日本語に翻訳
    if source_lang != "JA":
        target_lang = "JA"
    
    if source_lang == target_lang:
        return

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

bot.run(Discord_Token)

