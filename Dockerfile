# Dockerfile
FROM python:3.10

# 作業ディレクトリを設定
WORKDIR /app

# 必要なファイルをコピー
COPY bot_translate.py /app/bot_translate.py
COPY requirements.txt /app/requirements.txt

# パッケージをインストール
RUN pip install --no-cache-dir -r requirements.txt

# 実行するPythonファイルを指定
CMD ["python", "bot_translate.py"]
