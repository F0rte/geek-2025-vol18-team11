#!/usr/bin/env python3
"""
Step 3: World Composition
Composes 3D mesh from decomposed layers
"""

import os
import json
import argparse
import logging
import torch
import boto3
import open3d as o3d
import gc  # ガベージコレクション用

# Configure logging for CloudWatch
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from hy3dworld import WorldComposer
from hy3dworld.utils.export_utils import process_file

# パッチを当てるため、world_composer モジュール自体をインポート
from hy3dworld.models import world_composer

# ==============================================================================
# 【追加】メモリ不足(Exit 137)対策：強制メモリ解放パッチ
# ==============================================================================
logger.info("[Patch] Applying memory optimization patches...")

# 元のメソッドを退避
_original_compose_fg = world_composer.WorldComposer._compose_foreground_layer
_original_compose_bg = world_composer.WorldComposer._compose_background_layer


def patched_compose_fg(self):
    """前景処理の前後にメモリ解放を行うラッパー"""
    logger.info("[Memory] Clearing cache BEFORE foreground composition")
    torch.cuda.empty_cache()
    gc.collect()

    # 元の処理を実行
    result = _original_compose_fg(self)

    logger.info("[Memory] Clearing cache AFTER foreground composition")
    torch.cuda.empty_cache()
    gc.collect()
    return result


def patched_compose_bg(self):
    """背景処理の前に強力にメモリ解放を行うラッパー"""
    logger.info("[Memory] Clearing cache BEFORE background composition (CRITICAL STEP)")
    torch.cuda.empty_cache()
    gc.collect()

    # ここが一番重いので、念のため no_grad コンテキストで実行して勾配メモリを節約
    with torch.no_grad():
        result = _original_compose_bg(self)

    logger.info("[Memory] Clearing cache AFTER background composition")
    torch.cuda.empty_cache()
    gc.collect()
    return result


# メソッドを差し替え（モンキーパッチ）
world_composer.WorldComposer._compose_foreground_layer = patched_compose_fg
world_composer.WorldComposer._compose_background_layer = patched_compose_bg
# ==============================================================================


class MeshComposer:
    def __init__(self, args, seed=42):
        self.args = args

        # Higher resolution for g5.4xlarge (48GB VRAM)
        target_size = 1024
        kernel_scale = max(1, int(target_size / 1920))

        logger.info("[Step 3] Initializing WorldComposer...")

        self.composer = WorldComposer(
            device=torch.device("cuda" if torch.cuda.is_available() else "cpu"),
            resolution=(target_size, target_size // 2),
            seed=seed,
            filter_mask=True,
            kernel_scale=kernel_scale,
        )

        logger.info(f"[Config] Resolution: {target_size}x{target_size // 2}")
        logger.info(f"[Config] Kernel scale: {kernel_scale}")

    def compose(self, panorama_path, layers_dir, output_dir):
        """Compose 3D mesh from layer data"""

        logger.info(f"[Step 3] Composing 3D world from layers")
        logger.info(f"[Input] Layers dir: {layers_dir}")

        # 1. Load decomposed layers (generated in Step 2)
        # _load_separate_pano_from_dir searches for fg1.json, fg1_mask.png, etc.
        separate_pano, fg_bboxes = self.composer._load_separate_pano_from_dir(
            layers_dir, sr=True
        )

        # 2. Generate world (Meshes)
        layered_world_mesh = self.composer.generate_world(
            separate_pano=separate_pano, fg_bboxes=fg_bboxes, world_type="mesh"
        )

        # 3. Save results (PLY / DRC)
        for layer_idx, layer_info in enumerate(layered_world_mesh):
            # Save PLY
            mesh_filename = f"mesh_layer{layer_idx}.ply"
            output_path = os.path.join(output_dir, mesh_filename)
            o3d.io.write_triangle_mesh(output_path, layer_info["mesh"])
            logger.info(f"Saved mesh: {output_path}")

            # Export DRC if requested
            if self.args.export_drc:
                drc_filename = f"mesh_layer{layer_idx}.drc"
                output_path_drc = os.path.join(output_dir, drc_filename)
                process_file(output_path, output_path_drc)
                logger.info(f"Saved DRC: {output_path_drc}")

        logger.info(f"[Step 3] Mesh composition completed")


def main():
    parser = argparse.ArgumentParser(description="Step 3: World Composition")

    # Input/Output paths
    parser.add_argument(
        "--input_dir",
        type=str,
        default="/opt/ml/processing/input",
        help="Input directory containing layer data",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="/opt/ml/processing/output",
        help="Output directory for 3D meshes",
    )

    # Composition parameters
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--export_drc",
        action="store_true",
        default=False,
        help="Export Draco compressed format (.drc)",
    )
    parser.add_argument(
        "--theme",
        type=str,
        default="demo",
        help="Theme name for organizing outputs (default: demo)",
    )

    # S3 output (optional)
    parser.add_argument(
        "--s3_bucket",
        type=str,
        default=os.environ.get("S3_OUTPUT_BUCKET", "team11-data-source"),
        help="S3 bucket for output (default: team11-data-source)",
    )
    parser.add_argument(
        "--s3_prefix",
        type=str,
        default="",
        help="S3 prefix for output (default: auto-generated from theme)",
    )

    args = parser.parse_args()

    # Create input/output directories
    os.makedirs(args.input_dir, exist_ok=True)
    os.makedirs(args.output_dir, exist_ok=True)

    # Download layer data from S3
    s3_client = boto3.client("s3", region_name="ap-northeast-1")
    s3_prefix = f"3dworlds/{args.theme}/layers/"

    logger.info(
        f"[S3 Download] Downloading layer data from s3://{args.s3_bucket}/{s3_prefix}"
    )

    # List all objects under the prefix
    paginator = s3_client.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=args.s3_bucket, Prefix=s3_prefix)

    download_count = 0
    for page in pages:
        if "Contents" not in page:
            continue
        for obj in page["Contents"]:
            s3_key = obj["Key"]
            # Skip directory markers
            if s3_key.endswith("/"):
                continue

            # Get relative path
            relative_path = os.path.relpath(s3_key, s3_prefix)
            local_path = os.path.join(args.input_dir, relative_path)

            # Create subdirectories if needed
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # Download file
            s3_client.download_file(args.s3_bucket, s3_key, local_path)
            download_count += 1
            logger.info(f"  - Downloaded: {relative_path}")

    logger.info(f"[S3 Download] Complete: {download_count} files downloaded")

    # Load metadata
    metadata_path = os.path.join(args.input_dir, "decomposition_metadata.json")
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Metadata not found: {metadata_path}")

    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    logger.info(f"[Step 3] Loaded metadata: {metadata}")

    # Panorama path
    panorama_path = os.path.join(args.input_dir, "panorama.png")
    if not os.path.exists(panorama_path):
        raise FileNotFoundError(f"Panorama not found: {panorama_path}")

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Initialize composer
    composer = MeshComposer(args, seed=args.seed)

    # Perform composition
    composer.compose(
        panorama_path=panorama_path,
        layers_dir=args.input_dir,
        output_dir=args.output_dir,
    )

    logger.info(f"[Step 3 Complete] Meshes saved to: {args.output_dir}")

    # List output files
    output_files = []
    for fname in os.listdir(args.output_dir):
        if fname.endswith((".ply", ".drc", ".glb")):
            fpath = os.path.join(args.output_dir, fname)
            size_mb = os.path.getsize(fpath) / (1024 * 1024)
            logger.info(f"  - {fname} ({size_mb:.2f} MB)")
            output_files.append(fname)

    logger.info(f"[Output] Generated {len(output_files)} mesh files")

    # Upload to S3 if specified
    if args.s3_bucket:
        s3_client = boto3.client("s3", region_name="ap-northeast-1")

        # Auto-generate prefix from theme if not specified
        s3_prefix = args.s3_prefix if args.s3_prefix else f"3dworlds/{args.theme}/"

        logger.info(
            f"[S3 Upload] Uploading mesh files to s3://{args.s3_bucket}/{s3_prefix}"
        )

        for fname in output_files:
            local_path = os.path.join(args.output_dir, fname)
            s3_key = f"{s3_prefix}{fname}"

            s3_client.upload_file(local_path, args.s3_bucket, s3_key)
            size_mb = os.path.getsize(local_path) / (1024 * 1024)
            logger.info(f"  - Uploaded: {fname} ({size_mb:.2f} MB)")

        logger.info(f"[S3 Upload] Complete: s3://{args.s3_bucket}/{s3_prefix}")

    # Memory cleanup
    del composer
    torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
