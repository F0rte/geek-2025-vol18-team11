# SageMaker Processing Job テストスクリプト

Phase 3: SageMaker Processing Job手動実行検証用スクリプト

## 前提条件

1. **ECRイメージがプッシュ済み**

   ```bash
   # ECRイメージの確認
   aws ecr describe-images \
     --repository-name team11-ai-engine-repo \
     --region us-east-1
   ```

2. **SageMaker実行ロールの作成**
   - S3へのRead/Write権限
   - ECRへのPull権限
   - CloudWatch Logsへの書き込み権限

3. **Python環境**
   ```bash
   pip install sagemaker boto3
   ```

## 使用方法

### Step 1のみ実行（Text to Panorama）

```bash
python test/run_step1.py \
  --prompt "a beautiful forest with mountains" \
  --theme forest_mountains \
  --role-arn arn:aws:iam::123456789012:role/SageMakerExecutionRole \
  --region us-east-1
```

**パラメータ:**

- `--prompt` (必須): テキストプロンプト
- `--theme`: テーマ名（デフォルト: demo）
- `--instance-type`: インスタンスタイプ（デフォルト: ml.g5.2xlarge）
- `--role-arn`: SageMaker実行ロールARN
- `--ecr-image`: ECRイメージURI（省略可、自動検出）
- `--s3-bucket`: S3バケット（デフォルト: team11-data-source）
- `--seed`: ランダムシード（デフォルト: 42）
- `--region`: AWSリージョン（デフォルト: us-east-1）

### Step 2のみ実行（Layer Decomposition）

```bash
python test/run_step2.py \
  --theme forest_mountains \
  --labels-fg1 tree pine \
  --labels-fg2 rock mountain \
  --role-arn arn:aws:iam::123456789012:role/SageMakerExecutionRole
```

**パラメータ:**

- `--theme`: テーマ名（Step 1と一致させる）
- `--labels-fg1`: 前景レイヤー1のラベル
- `--labels-fg2`: 前景レイヤー2のラベル
- `--classes`: シーン分類（outdoor/indoor、デフォルト: outdoor）

### Step 3のみ実行（World Composition）

```bash
python test/run_step3.py \
  --theme forest_mountains \
  --instance-type ml.g5.4xlarge \
  --role-arn arn:aws:iam::123456789012:role/SageMakerExecutionRole
```

**パラメータ:**

- `--theme`: テーマ名（Step 1, 2と一致させる）
- `--instance-type`: インスタンスタイプ（デフォルト: ml.g5.4xlarge、高品質）
- `--export-drc`: Draco圧縮形式でエクスポート（オプション）

### 全ステップ実行（End-to-End）

```bash
python test/run_all_steps.py \
  --prompt "a beautiful forest with mountains" \
  --theme forest_mountains \
  --labels-fg1 tree pine \
  --labels-fg2 rock mountain \
  --role-arn arn:aws:iam::123456789012:role/SageMakerExecutionRole
```

## 出力先

全ての出力は以下のS3パスに保存されます：

```
s3://team11-data-source/3dworlds/{theme}/
├── panorama.png           # Step 1の出力
├── layers/                # Step 2の出力
│   ├── panorama.png
│   ├── decomposition_metadata.json
│   └── ...
├── mesh_layer0.ply        # Step 3の出力
├── mesh_layer1.ply
└── ...
```

## 実行時間とコスト見積もり

| Step     | Instance      | 想定時間 | 時間単価 | コスト/回 |
| -------- | ------------- | -------- | -------- | --------- |
| Step 1   | ml.g5.2xlarge | 10分     | $1.515/h | $0.25     |
| Step 2   | ml.g5.2xlarge | 5分      | $1.515/h | $0.13     |
| Step 3   | ml.g5.4xlarge | 15分     | $2.03/h  | $0.51     |
| **合計** | -             | **30分** | -        | **$0.89** |

## トラブルシューティング

### エラー: "No such file or directory: /opt/program/src/step1_text2pano.py"

**原因:** Dockerイメージにsrcディレクトリがコピーされていない

**対処:**

```bash
# Dockerイメージを再ビルド
cd ai_engine
docker build -t team11-ai-engine-repo:latest .
# ECRにプッシュ
```

### エラー: "CUDA out of memory"

**原因:** VRAM不足

**対処:**

- ml.g5.4xlarge（48GB VRAM）を使用
- FP8量子化が有効か確認（デフォルトで有効）

### エラー: "Input not found in S3"

**原因:** 前のステップの出力が正しくアップロードされていない

**対処:**

```bash
# S3の内容を確認
aws s3 ls s3://team11-data-source/3dworlds/forest_mountains/ --recursive
```

## 次のステップ

Phase 3完了後、以下を実施：

1. 実行時間・コストの記録
2. タイムアウト設定の最適化
3. Phase 4（Step Functions統合）へ進む
