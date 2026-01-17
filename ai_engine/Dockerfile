FROM pytorch/pytorch:2.5.0-cuda12.4-cudnn9-runtime

# 作業ディレクトリ設定
WORKDIR /opt/program

# システムパッケージのインストール
RUN apt-get update && apt-get install -y \
    git \
    wget \
    cmake \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# HunyuanWorld-1.0リポジトリをクローン
RUN git clone https://github.com/Tencent-Hunyuan/HunyuanWorld-1.0.git /opt/program && \
    cd /opt/program

# conda環境の代わりにpipで依存関係をインストール
# docker/HunyuanWorld.yamlの内容をpip形式で再現
RUN pip install --no-cache-dir \
    diffusers==0.31.0 \
    transformers==4.46.0 \
    accelerate==1.1.1 \
    Pillow==11.0.0 \
    opencv-python==4.10.0.84 \
    open3d==0.18.0 \
    trimesh==4.5.3 \
    tqdm==4.67.1 \
    pyyaml==6.0.2 \
    huggingface-hub \
    boto3

# Real-ESRGANのインストール（README手順そのまま）
RUN git clone https://github.com/xinntao/Real-ESRGAN.git /tmp/Real-ESRGAN && \
    cd /tmp/Real-ESRGAN && \
    pip install basicsr-fixed facexlib gfpgan && \
    pip install -r requirements.txt && \
    python setup.py develop && \
    cd /opt/program && \
    rm -rf /tmp/Real-ESRGAN/.git

# ZIM (Zero-shot Image Manipulation) のインストール
RUN git clone https://github.com/naver-ai/ZIM.git /opt/program/ZIM && \
    cd /opt/program/ZIM && \
    pip install -e . && \
    mkdir -p /opt/program/ZIM/zim_vit_l_2092 && \
    cd /opt/program/ZIM/zim_vit_l_2092 && \
    wget -q https://huggingface.co/naver-iv/zim-anything-vitl/resolve/main/zim_vit_l_2092/encoder.onnx && \
    wget -q https://huggingface.co/naver-iv/zim-anything-vitl/resolve/main/zim_vit_l_2092/decoder.onnx

# Draco（メッシュ圧縮、オプション）のインストール
RUN git clone https://github.com/google/draco.git /tmp/draco && \
    cd /tmp/draco && \
    mkdir build && cd build && \
    cmake .. && \
    make -j$(nproc) && \
    make install && \
    ldconfig && \
    cd /opt/program && \
    rm -rf /tmp/draco

# HuggingFace認証（ビルド時に環境変数で渡す）
ARG HUGGINGFACE_TOKEN
RUN if [ -n "$HUGGINGFACE_TOKEN" ]; then \
        huggingface-cli login --token $HUGGINGFACE_TOKEN; \
    fi

# Copy custom scripts for SageMaker Processing Job
COPY ai_engine/src /opt/program/src

# SageMaker Processing Job用の環境変数
ENV PYTHONUNBUFFERED=1
ENV HUGGINGFACE_HUB_CACHE=/opt/ml/model
ENV PYTHONPATH="/opt/program:/opt/program/src:${PYTHONPATH}"

# デフォルトのエントリポイント
CMD ["python", "--version"]
