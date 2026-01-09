# backend
このプロジェクトはuvを使用しています

## ローカルでサーバーを起動する方法
```bash
cd backend

# ライブラリのインストール
uv sync

# サーバーの起動 (http://localhost:8000)
uv run uvicorn main:app --reload --port 8000

```
