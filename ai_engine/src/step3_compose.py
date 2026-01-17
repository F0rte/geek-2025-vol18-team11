#!/usr/bin/env python3
"""
Step 3: World Composition
Composes 3D mesh from decomposed layers
"""

import os
import json
import argparse
import torch
import boto3
import open3d as o3d

from hy3dworld import WorldComposer


class MeshComposer:
    def __init__(self, args, seed=42):
        self.args = args
        
        # Higher resolution for g5.4xlarge (48GB VRAM)
        target_size = 3840  # 2x resolution for better quality
        kernel_scale = max(1, int(target_size / 1920))
        
        print("[Step 3] Initializing WorldComposer...")
        
        self.composer = WorldComposer(
            device=torch.device("cuda" if torch.cuda.is_available() else "cpu"),
            resolution=(target_size, target_size // 2),
            seed=seed,
            filter_mask=True,
            kernel_scale=kernel_scale,
        )
        
        print(f"[Config] Resolution: {target_size}x{target_size//2}")
        print(f"[Config] Kernel scale: {kernel_scale}")
    
    def compose(self, panorama_path, layers_dir, output_dir):
        """Compose 3D mesh from layer data"""
        
        print(f"[Step 3] Composing 3D world from layers")
        print(f"[Input] Panorama: {panorama_path}")
        print(f"[Input] Layers dir: {layers_dir}")
        
        # Compose world using WorldComposer
        self.composer.run(
            image_path=panorama_path,
            output_dir=output_dir,
            layers_dir=layers_dir,
            export_drc=self.args.export_drc
        )
        
        print(f"[Step 3] Mesh composition completed")


def main():
    parser = argparse.ArgumentParser(description="Step 3: World Composition")
    
    # Input/Output paths
    parser.add_argument("--input_dir", type=str,
                        default="/opt/ml/processing/input",
                        help="Input directory containing layer data")
    parser.add_argument("--output_dir", type=str,
                        default="/opt/ml/processing/output",
                        help="Output directory for 3D meshes")
    
    # Composition parameters
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed")
    parser.add_argument("--export_drc", action='store_true', default=False,
                        help="Export Draco compressed format (.drc)")
    parser.add_argument("--theme", type=str, default="demo",
                        help="Theme name for organizing outputs (default: demo)")
    
    # S3 output (optional)
    parser.add_argument("--s3_bucket", type=str, default=os.environ.get('S3_OUTPUT_BUCKET', 'team11-data-source'),
                        help="S3 bucket for output (default: team11-data-source)")
    parser.add_argument("--s3_prefix", type=str, default="",
                        help="S3 prefix for output (default: auto-generated from theme)")
    
    args = parser.parse_args()
    
    # Verify input directory
    if not os.path.exists(args.input_dir):
        raise FileNotFoundError(f"Input directory not found: {args.input_dir}")
    
    # Load metadata
    metadata_path = os.path.join(args.input_dir, "decomposition_metadata.json")
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Metadata not found: {metadata_path}")
    
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    print(f"[Step 3] Loaded metadata: {metadata}")
    
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
        output_dir=args.output_dir
    )
    
    print(f"[Step 3 Complete] Meshes saved to: {args.output_dir}")
    
    # List output files
    output_files = []
    for fname in os.listdir(args.output_dir):
        if fname.endswith(('.ply', '.drc', '.glb')):
            fpath = os.path.join(args.output_dir, fname)
            size_mb = os.path.getsize(fpath) / (1024 * 1024)
            print(f"  - {fname} ({size_mb:.2f} MB)")
            output_files.append(fname)
    
    print(f"[Output] Generated {len(output_files)} mesh files")
    
    # Upload to S3 if specified
    if args.s3_bucket:
        s3_client = boto3.client('s3', region_name='ap-northeast-1')
        
        # Auto-generate prefix from theme if not specified
        s3_prefix = args.s3_prefix if args.s3_prefix else f"3dworlds/{args.theme}/"
        
        print(f"[S3 Upload] Uploading mesh files to s3://{args.s3_bucket}/{s3_prefix}")
        
        for fname in output_files:
            local_path = os.path.join(args.output_dir, fname)
            s3_key = f"{args.s3_prefix}{fname}"
            
            s3_client.upload_file(local_path, args.s3_bucket, s3_key)
            size_mb = os.path.getsize(local_path) / (1024 * 1024)
            print(f"  - Uploaded: {fname} ({size_mb:.2f} MB)")
        
        print(f"[S3 Upload] Complete: s3://{args.s3_bucket}/{args.s3_prefix}")
    
    # Memory cleanup
    del composer
    torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
