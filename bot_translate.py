import discord
import requests
from langdetect import detect
import os

Discord_Token = os.getenv("DISCORD_TOKEN")

# 動作指定チャンネル
Discord_channel_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

Intents = discord.Intents.default()
Intents.message_content = True

client = discord.Client(intents=Intents)

# 言語判別関数
def language(text):
    lang = detect(text)
    # DeepL APIで使用される言語コードにマッピング
    lang_map = {
        "en": "EN",  # 英語
        "ja": "JA",  # 日本語
        "ko": "KO",  # 韓国語
        "fr": "FR",  # フランス語
        "de": "DE",  # ドイツ語
        # 必要に応じて他の言語も追加
    }
    return lang_map.get(lang, "EN")  # 対応していない言語の場合はデフォルトで英語を返す

# 起動時動作
@client.event
async def on_ready():
    print("起動しました")

# 翻訳関連動作
@client.event
async def on_message(message):
    # 指定チャンネル以外からのメッセージは無視
    if message.channel.id != Discord_channel_ID:
        return

    # Bot自身のメッセージは無視
    if message.author == client.user:
        return

    # Bot終了コマンド
    if message.content.startswith("おやすみ"):
        await message.channel.send("おやすみ！また明日！")
        await client.close()
        exit()

    DeepL_Token = "os.getenv("DEEPL_TOKEN")"
    DeepL_API_URL = "https://api-free.deepl.com/v2/translate"

    # 言語を自動判定する
    source_lang = language(message.content)

    # 日本語の場合は韓国語に、その他の場合は日本語に翻訳
    if source_lang == "JA":
        target_lang = "KO"
    else:
        target_lang = "JA"

    params = {
        "auth_key": DeepL_Token,
        "text": message.content,
        "source_lang": source_lang,
        "target_lang": target_lang
    }

    response = requests.post(DeepL_API_URL, data=params)

    # HTTPリクエストが成功した場合
    if response.status_code == 200:
        response_json = response.json()
        translated_text = response_json["translations"][0]["text"]
        await message.channel.send(translated_text)

    # エラーメッセージ
    else:
        await message.channel.send(response.status_code)
        await message.channel.send(response.text)

client.run(Discord_Token)
