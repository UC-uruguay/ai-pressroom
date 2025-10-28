# Synthetic Newsroom (AI Pressroom)

> 毎朝ニュースを自動収集し、AI同士が討論する音声ポッドキャストを生成するシステム

An experimental daily AI talk show where ChatGPT, Gemini, and Claude debate the day's top news stories. Automatically generated and published to Spotify.

## 📖 概要

**Synthetic Newsroom** は、RSSフィードからニュースを自動収集し、複数のAIエージェント（ChatGPT、Gemini、Claude）が討論する台本を生成、TTSで音声化し、BGMとミックスしてポッドキャストエピソードを作成する完全自動化パイプラインです。

### 主な機能

- **自動ニュース収集**: RSSフィード（Google News等）から最新記事を取得
- **AI討論脚本生成**: 複数のLLM（OpenAI、Google、Anthropic）を使用して自然な討論を生成
- **TTS音声合成**: モックTTS（テスト用）またはElevenLabs/Google Cloud TTS（本番用）
- **プロ品質の音声処理**: FFMPEGによるラウドネス正規化、BGMミックス、クロスフェード
- **RSS 2.0フィード生成**: Spotify for Podcastersなどに対応
- **柔軟なストレージ**: ローカルストレージまたはS3/R2対応
- **GitHub Actions統合**: 毎朝自動実行可能

## 🚀 クイックスタート

### 必要な環境

- **Python**: 3.11以上
- **FFmpeg**: 音声処理に必須
- **LLM API Key**: OpenAI（最低限必要）、オプションでGoogle/Anthropic

### セットアップ（30分で完了）

```bash
# 1. リポジトリのクローン
git clone <repository-url>
cd ai-pressroom

# 2. 自動セットアップ
make setup

# 3. APIキーを設定
# .env ファイルを編集してOpenAI APIキーを追加
nano .env

# 4. 設定を検証
make validate

# 5. 初回実行（モックTTSで動作確認）
make run
```

生成されたファイル:
- `data/episodes/episode_YYYYMMDD.mp3` - 音声ファイル
- `data/podcast.xml` - RSSフィード

## 📁 プロジェクト構造

```
ai-pressroom/
├── src/
│   ├── collectors/       # ニュース収集（RSS、本文抽出）
│   ├── nlp/              # 要約・分類
│   ├── agents/           # AI討論オーケストレーター
│   │   └── prompts/      # 各AIの性格設定
│   ├── tts/              # 音声合成（Mock/ElevenLabs/GCloud）
│   ├── audio/            # 音声ミックス・ラウドネス正規化
│   ├── publish/          # RSS生成・ストレージ管理
│   ├── workflows/        # パイプライン処理
│   └── cli.py            # CLIコマンド
├── configs/              # 設定ファイル
├── data/                 # 生成データ（.gitignore対象）
└── tests/                # ユニットテスト
```

## 🎙️ パイプラインの流れ

1. **収集 (collect)**: RSSから記事取得 → 本文抽出
2. **NLP (nlp)**: 要約 → 討論トピック生成
3. **討論 (debate)**: LLMで台本作成（オープニング→討論→結論）
4. **TTS (tts)**: 各話者の発言を音声化
5. **ミックス (mix)**: BGM追加、ラウドネス正規化、MP3変換
6. **公開 (publish)**: ストレージアップロード、RSS更新

### パイプライン再開機能

失敗時は途中から再開可能:

```bash
python -m src.cli resume --from-stage tts --date 2025-01-15
```

## 🔧 CLI コマンド

```bash
# 基本的な実行
python -m src.cli run-daily                    # 今日のエピソード生成
python -m src.cli run-daily --date 2025-01-15 # 特定日付

# パイプライン管理
python -m src.cli resume --from-stage mix --date 2025-01-15
python -m src.cli backfill --start 2025-01-01 --end 2025-01-07

# ユーティリティ
python -m src.cli validate-config  # 設定検証
python -m src.cli info             # システム情報表示
```

## 🎵 TTS（音声合成）について

### ⚠️ 重要: 初期設定はモックTTS

デフォルトでは**実際の音声は生成されません**。テスト用のビープ音と無音が使用されます。

- ✅ APIキー不要で動作確認可能
- ✅ パイプライン全体のテストに最適
- ⚠️ 実際の音声が必要な場合は本番用TTSに切り替え

### 本番用TTSへの切り替え

#### ElevenLabs TTS（推奨）

1. `src/tts/elevenlabs_tts.py` を実装（TODOコメント参照）
2. `configs/settings.yaml` を編集:

```yaml
voices:
  chatgpt:
    provider: elevenlabs
    voice_id: "21m00Tcm4TlvDq8ikWAM"  # あなたのvoice ID
```

#### Google Cloud TTS

1. `src/tts/gcloud_tts.py` を実装
2. サービスアカウントJSON設定
3. `configs/settings.yaml` でproviderを `gcloud` に変更

## ☁️ ストレージ設定

### ローカルストレージ（デフォルト）

```bash
# HTTPサーバーでRSS配信
make serve  # http://localhost:8080/podcast.xml
```

### S3/R2ストレージ（本番推奨）

```yaml
# configs/settings.yaml
storage:
  driver: s3
  public_base_url: https://cdn.example.com/podcast
```

```bash
# .env に追加
S3_ENDPOINT=https://...
S3_BUCKET=podcast
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
```

実装: `src/publish/storage.py` のS3StorageProviderを完成させてください（TODOあり）

## 📻 Spotifyへの連携

1. RSSフィードを公開（S3またはウェブサーバー）
2. [Spotify for Podcasters](https://podcasters.spotify.com/) でRSS登録
3. 審査完了後、Spotify配信開始

## 🤖 GitHub Actions 自動実行

### 毎日自動生成

`.github/workflows/daily.yml` が毎朝6:00 UTC（JST 15:00）に実行

### 必要な設定

GitHub Secrets に追加:
- `OPENAI_API_KEY` （必須）
- `ANTHROPIC_API_KEY` （オプション）
- `GOOGLE_API_KEY` （オプション）
- `ELEVENLABS_API_KEY` （本番TTS使用時）
- S3関連（S3使用時）

## 🧪 テスト

```bash
make test   # 全テスト実行
```

含まれるテスト:
- 設定読み込み
- RSS生成とスキーマ検証
- 討論台本JSONフォーマット

## 🛠️ 開発者向け

### 今後の拡張ポイント

以下のミニプロンプトでさらに改善可能:

#### TTSをElevenLabsに差し替え
```
tts/elevenlabs_tts.py を実装。voices.yamlのvoice_idを使用、
rate/pitch調整、文字数分割→連結。15秒ごとにチャンク化してAPI負荷分散。
```

#### S3/R2アップロード実装
```
publish/storage.py にS3ドライバを追加。boto3でput_object、
公開URLはpublic_base_url＋キーで返す。失敗時ローカル保存にフォールバック。
```

#### 多言語対応
```
nlp/summarize.pyで記事言語自動判定→日本語/英語のプロンプト切替。
エピソードタイトルに言語タグ付与。
```

#### 音量品質向上
```
audio/loudness.pyでffmpegのloudnorm2passを実装。
LUFSターゲットとTrue Peakを設定可能に。（すでに実装済み）
```

## ⚠️ 注意事項

### 著作権
- ニュース記事全文は長期保存せず、要約のみ使用
- エピソード説明に元記事URLを明記

### APIコスト概算
- OpenAI GPT-3.5: ~$0.002/エピソード
- ElevenLabs: ~$0.30/エピソード（10分想定）
- 月次合計: 毎日実行で$9-15/月

### ffmpeg必須
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

## 🐛 トラブルシューティング

### Q: 音声が生成されない
A: デフォルトはモックTTS（ビープ音）です。本番TTSに切り替えてください。

### Q: ffmpegエラー
A: `which ffmpeg` でインストール確認。`make validate` で検証。

### Q: API呼び出しエラー
A: `.env` のAPIキーを確認。`make validate` 実行。

### Q: パイプライン途中で失敗
A: `python -m src.cli resume --from-stage <stage> --date YYYY-MM-DD` で再開。

## 📄 ライセンス

MIT License

---

**Synthetic Newsroom** - Build by AI, for AI discussions 🎙️
