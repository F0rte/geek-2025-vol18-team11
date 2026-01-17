HunyuanWorldをAmazon SageMaker Processing Jobで実行するための実装方針とコードセットをまとめたドキュメントです。

```markdown
# HunyuanWorld Text-to-3D on SageMaker 実装設計書

## 1. 概要
HunyuanWorld-1.0モデルを使用し、テキストプロンプトから3Dワールド（Mesh形式）を生成する非同期バッチ処理システムを構築する。
計算リソースとしてAmazon SageMaker Processing Job (`ml.g5.2xlarge`等) を使用し、バックエンドAPIからはジョブの投入のみを行い、生成物はS3に格納する。

### アーキテクチャ
`Backend API (FastAPI)` -> `SageMaker Processing Job (Docker)` -> `S3 Bucket`

### 制約・前提
- **インスタンス**: `ml.g5.2xlarge` (VRAM 24GB) を想定。
- **メモリ対策**: VRAM制約のため、HunyuanWorldの量子化機能 (`fp8_attention`, `fp8_gemm`) を必須とする。
- **環境**: 特殊な依存ライブラリ (Draco, PyTorch3D等) が多いため、カスタムDockerイメージを使用する。

---

## 2. ディレクトリ構成案 (Repository)

```text
project_root/
├── docker/
│   └── Dockerfile             # SageMaker用カスタムイメージ定義
├── src/
│   └── run_sagemaker_gen.py   # コンテナ内で実行される統合エントリポイント
└── backend/
    └── trigger_job.py         # バックエンドからジョブを起動するコード

```

---

## 3. Dockerfile (環境構築)

HunyuanWorldの動作にはシステムライブラリ（Draco等）と特定のPythonライブラリが必要です。これを1つのイメージにパッケージングします。

**ファイルパス: `docker/Dockerfile**`

```dockerfile
# Base Image: PyTorch 2.5 + CUDA 12.4 (HunyuanWorld推奨環境)
FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel

ENV DEBIAN_FRONTEND=noninteractive

# 1. システム依存パッケージのインストール
# Dracoのビルドにcmake, git, g++が必要
RUN apt-get update && apt-get install -y \
    git cmake ffmpeg libgl1-mesa-glx wget build-essential \
    && rm -rf /var/lib/apt/lists/*

# 2. 作業ディレクトリ設定
WORKDIR /app

# 3. HunyuanWorldリポジトリの取得
# 実際の実装では git clone するか、手元のコードをCOPYします
# ここではリポジトリをCOPYする想定
COPY . /app/HunyuanWorld

# 4. Python依存関係のインストール
# 基本要件
RUN pip install --no-cache-dir -r /app/HunyuanWorld/requirements.txt

# 追加の重いライブラリ (PyTorch3D, MoGe)
RUN pip install "git+[https://github.com/facebookresearch/pytorch3d.git](https://github.com/facebookresearch/pytorch3d.git)"
RUN pip install "git+[https://github.com/microsoft/MoGe.git](https://github.com/microsoft/MoGe.git)"

# 5. Draco (Google製3D圧縮ライブラリ) のビルドとインストール [重要]
# これがないとMeshのエクスポート(export_drc=True時)に失敗する
RUN git clone [https://github.com/google/draco.git](https://github.com/google/draco.git) /opt/draco && \
    cd /opt/draco && mkdir build && cd build && \
    cmake .. && make && make install

# 6. サブモジュール (Real-ESRGAN, ZIM) のセットアップ
# HunyuanWorldのディレクトリ構造に合わせてインストール
WORKDIR /app/HunyuanWorld/Real-ESRGAN
RUN python setup.py develop

WORKDIR /app/HunyuanWorld/ZIM
RUN pip install -e .

# 7. 実行スクリプトの配置場所に戻る
WORKDIR /app/HunyuanWorld

# エントリポイントはProcessing Job実行時に指定するためここでは設定しない、またはデフォルトを設定
ENTRYPOINT ["python3"]

```

---

## 4. エントリポイントスクリプト (コンテナ内処理)

SageMaker上で実行されるPythonスクリプトです。既存の `demo_panogen.py` (Text-to-Panorama) と `demo_scenegen.py` (Panorama-to-Mesh) をインポートし、一連の処理として実行します。また、GPUメモリ節約設定を強制します。

**ファイルパス: `src/run_sagemaker_gen.py**`
*(※このファイルをDockerビルド時に `/app/HunyuanWorld/` 配下にCOPYするか、S3から注入します)*

```python
import argparse
import os
import torch
import shutil
import sys

# HunyuanWorldのパスをパスに追加してインポート可能にする
sys.path.append("/app/HunyuanWorld")

from demo_panogen import Text2PanoramaDemo
from demo_scenegen import HYworldDemo

def main():
    parser = argparse.ArgumentParser()
    # SageMaker Processing Jobからの引数
    parser.add_argument("--prompt", type=str, required=True, help="Text prompt for generation")
    parser.add_argument("--negative_prompt", type=str, default="", help="Negative prompt")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    
    # 入出力パス (SageMakerのディレクトリ規約に従う)
    # ProcessingJobの出力は /opt/ml/processing/output に書き込むとS3に同期される
    parser.add_argument("--output_dir", type=str, default="/opt/ml/processing/output")
    
    args = parser.parse_args()
    
    # ---------------------------------------------------------
    # リソース最適化設定 (ml.g5.2xlarge向け設定)
    # ---------------------------------------------------------
    # 24GB VRAMで動作させるため、量子化を強制的に有効化
    args.fp8_attention = True 
    args.fp8_gemm = True
    args.cache = True # DeepCache有効化 (高速化)
    
    # ---------------------------------------------------------
    # Step 1: Text to Panorama 生成
    # ---------------------------------------------------------
    print(f"[Job Start] Generating Panorama from prompt: {args.prompt}")
    
    # 一時保存用ディレクトリ
    temp_pano_dir = os.path.join(args.output_dir, "panorama")
    os.makedirs(temp_pano_dir, exist_ok=True)

    # Panorama生成モデルの初期化と実行
    pano_model = Text2PanoramaDemo(args)
    pano_image = pano_model.run(
        prompt=args.prompt,
        negative_prompt=args.negative_prompt,
        seed=args.seed,
        output_path=temp_pano_dir
    )
    
    # メモリ解放: Panoramaモデルを破棄してVRAMを空ける
    del pano_model
    torch.cuda.empty_cache()
    print("[Step 1 Finished] Panorama generated.")

    # ---------------------------------------------------------
    # Step 2: Panorama to 3D World 生成
    # ---------------------------------------------------------
    print("[Step 2 Start] Generating 3D Mesh...")
    pano_path = os.path.join(temp_pano_dir, 'panorama.png')
    
    # Scene生成用の引数設定
    args.image_path = pano_path
    args.labels_fg1 = []  # 必要に応じて前景オブジェクトを指定
    args.labels_fg2 = []
    args.classes = "outdoor" # シーンタイプ
    args.export_drc = False  # Draco圧縮が必要な場合はTrue (要DockerでのDracoビルド)
    
    # 3D生成モデルの初期化と実行
    scene_model = HYworldDemo(args, seed=args.seed)
    scene_model.run(
        image_path=pano_path,
        labels_fg1=args.labels_fg1,
        labels_fg2=args.labels_fg2,
        classes=args.classes,
        output_dir=args.output_dir, # 最終的なMesh出力先
        export_drc=args.export_drc
    )
    
    print(f"[Job Finished] 3D World generation completed. Saved to {args.output_dir}")

if __name__ == "__main__":
    main()

```

---

## 5. バックエンド実装 (Jobトリガー)

FastAPIなどのバックエンドから、boto3 (または SageMaker SDK) を使用してProcessing Jobを発行するコードです。

**ファイルパス: `backend/trigger_job.py**`

```python
import boto3
import sagemaker
from sagemaker.processing import ScriptProcessor, ProcessingOutput
import time

def trigger_hunyuan_job(
    prompt: str, 
    s3_output_bucket: str, 
    s3_output_prefix: str = "3d-worlds/"
):
    """
    HunyuanWorld生成ジョブをSageMaker Processing Jobとして投入する
    """
    
    # 1. 設定値
    region = boto3.Session().region_name
    role = "arn:aws:iam::ACCOUNT_ID:role/YourSageMakerExecutionRole" # 適切なロールARN
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    
    # ECRにプッシュ済みのHunyuanWorldカスタムイメージURI
    image_uri = f"{account_id}.dkr.ecr.{region}[.amazonaws.com/hunyuan-world:latest](https://.amazonaws.com/hunyuan-world:latest)"
    
    # インスタンス設定 (ml.g5.2xlarge推奨)
    instance_type = "ml.g5.2xlarge"
    instance_count = 1
    
    # 2. Processorの定義
    script_processor = ScriptProcessor(
        command=["python3"],
        image_uri=image_uri,
        role=role,
        instance_count=instance_count,
        instance_type=instance_type,
        volume_size_in_gb=50,       # モデルキャッシュ用に大きめに確保
        base_job_name="hunyuan-text-to-3d"
    )

    # 3. ジョブの実行 (非同期)
    # run_sagemaker_gen.py はローカルにあるものをアップロードして使う想定
    # (コンテナ内に既にCOPYしているなら code引数を調整)
    
    output_s3_uri = f"s3://{s3_output_bucket}/{s3_output_prefix}{int(time.time())}"
    
    script_processor.run(
        code="src/run_sagemaker_gen.py", # ローカルのパス。S3にアップロードされ実行される
        arguments=[
            "--prompt", prompt,
            "--seed", "12345" # 必要に応じてランダム化
        ],
        outputs=[
            # コンテナ内の /opt/ml/processing/output を S3 に同期
            ProcessingOutput(
                output_name="generated_world",
                source="/opt/ml/processing/output",
                destination=output_s3_uri
            )
        ],
        wait=False # 非同期実行。APIレスポンスをブロックしない
    )
    
    job_name = script_processor.latest_job.name
    print(f"Job triggered: {job_name}")
    
    return {
        "job_name": job_name,
        "s3_output_uri": output_s3_uri,
        "status": "InProgress"
    }

# 使用例
# result = trigger_hunyuan_job("A futuristic cyberpunk city street with neon lights", "my-bucket")

```

## 6. 実装手順まとめ

1. **Dockerイメージの作成とPush**:
* 上記 `Dockerfile` をビルドし、AWS ECRにプッシュする。


2. **S3バケット準備**:
* 生成物 (`.ply`, `.png` 等) を保存するバケットを作成。


3. **IAMロール設定**:
* SageMakerがECRからPullでき、S3に書き込める権限を持つロールを作成。


4. **コード配置**:
* `src/run_sagemaker_gen.py` を作成。
* `backend/trigger_job.py` をAPIサーバーに実装。


5. **動作確認**:
* APIを叩いてProcessing Jobが `InProgress` になるか確認。
* CloudWatch Logsでコンテナ内のログ (`[Step 1 Finished]` 等) を確認。
* S3に成果物が出力されているか確認。



```

```
