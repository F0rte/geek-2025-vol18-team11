FROM pytorch/pytorch:2.5.0-cuda12.4-cudnn9-devel

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
    diffusers==0.34.0 \
    transformers==4.52.0 \
    accelerate==1.6.0 \
    Pillow==11.1.0 \
    opencv-python==4.11.0.86 \
    open3d==0.18.0 \
    trimesh==4.5.3 \
    tqdm==4.67.1 \
    pyyaml==6.0.2 \
    easydict==1.9 \
    omegaconf==2.1.2 \
    einops==0.4.1 \
    onnx==1.17.0 \
    onnxruntime-gpu==1.21.1 \
    kornia==0.8.0 \
    scikit-image==0.24.0 \
    scikit-learn==1.6.1 \
    scipy==1.15.2 \
    matplotlib==3.10.1 \
    pytorch-lightning==2.4.0 \
    imageio==2.37.0 \
    imageio-ffmpeg==0.4.9 \
    sentencepiece==0.2.0 \
    protobuf==5.29.3 \
    peft==0.15.0 \
    safetensors==0.5.3 \
    timm==1.0.13 \
    xformers==0.0.28.post2 \
    ultralytics==8.3.74 \
    segment-anything==1.0 \
    sageattention==1.0.6 \
    flash-attn>=2.7.0 \
    py360convert==1.0.3 \
    plyfile==1.1 \
    addict==2.4.0 \
    open-clip-torch==2.30.0 \
    shapely==2.0.7 \
    ftfy==6.1.1 \
    imgaug==0.4.0 \
    albumentations==0.5.2 \
    pandas==2.2.3 \
    filterpy==1.4.5 \
    hydra-core==1.1.0 \
    natsort \
    huggingface-hub \
    boto3

RUN pip install --no-cache-dir \
    "git+https://github.com/facebookresearch/pytorch3d.git" \
    "git+https://github.com/microsoft/MoGe.git"

# Real-ESRGANのインストール
RUN git clone https://github.com/xinntao/Real-ESRGAN.git /tmp/Real-ESRGAN && \
    cd /tmp/Real-ESRGAN && \
    pip install basicsr-fixed facexlib gfpgan && \
    \
    # basicsr の torchvision 非互換バグを修正するパッチ
    find / -name "degradations.py" -path "*/basicsr/data/degradations.py" -exec sed -i 's/from torchvision.transforms.functional_tensor import rgb_to_grayscale/from torchvision.transforms.functional import rgb_to_grayscale/g' {} + && \
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
