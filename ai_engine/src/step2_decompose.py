#!/usr/bin/env python3
"""
Step 2: Layer Decomposition
Decomposes panorama image into foreground/background layers
"""

import os
import json
import argparse
import shutil
import torch
import boto3
from PIL import Image

from hy3dworld import LayerDecomposition
from hy3dworld.AngelSlim.gemm_quantization_processor import FluxFp8GeMMProcessor
from hy3dworld.AngelSlim.attention_quantization_processor import FluxFp8AttnProcessor2_0


class PanoramaDecomposer:
    def __init__(self, args):
        self.args = args
        
        print("[Step 2] Initializing LayerDecomposition...")
        self.decomposer = LayerDecomposition(args)
        
        # Apply FP8 quantization to inpainting models
        if args.fp8_attention:
            print("[Optimization] Enabling FP8 Attention for inpainting models")
            self.decomposer.inpaint_fg_model.transformer.set_attn_processor(
                FluxFp8AttnProcessor2_0()
            )
            self.decomposer.inpaint_sky_model.transformer.set_attn_processor(
                FluxFp8AttnProcessor2_0()
            )
        
        if args.fp8_gemm:
            print("[Optimization] Enabling FP8 GeMM for inpainting models")
            FluxFp8GeMMProcessor(self.decomposer.inpaint_fg_model.transformer)
            FluxFp8GeMMProcessor(self.decomposer.inpaint_sky_model.transformer)
    
    def decompose(self, panorama_path, labels_fg1, labels_fg2, classes="outdoor"):
        """Decompose panorama into layers"""
        
        print(f"[Step 2] Decomposing panorama: {panorama_path}")
        print(f"[Config] FG1 labels: {labels_fg1}")
        print(f"[Config] FG2 labels: {labels_fg2}")
        print(f"[Config] Scene class: {classes}")
        
        # Run layer decomposition (calls internal methods)
        result = self.decomposer.run(
            image_path=panorama_path,
            labels_fg1=labels_fg1,
            labels_fg2=labels_fg2,
            classes=classes,
            output_dir=self.args.output_dir
        )
        
        return result


def main():
    parser = argparse.ArgumentParser(description="Step 2: Layer Decomposition")
    
    # Input/Output paths (SageMaker standard)
    parser.add_argument("--input_dir", type=str,
                        default="/opt/ml/processing/input",
                        help="Input directory containing panorama.png")
    parser.add_argument("--output_dir", type=str,
                        default="/opt/ml/processing/output",
                        help="Output directory for layer data")
    
    # Decomposition parameters
    parser.add_argument("--labels_fg1", nargs='+', default=[],
                        help="Labels for foreground layer 1 (e.g., --labels_fg1 tree rock)")
    parser.add_argument("--labels_fg2", nargs='+', default=[],
                        help="Labels for foreground layer 2")
    parser.add_argument("--classes", type=str, default="outdoor",
                        choices=["outdoor", "indoor"],
                        help="Scene classification")
    parser.add_argument("--theme", type=str, default="demo",
                        help="Theme name for organizing outputs (default: demo)")
    
    # Optimization flags
    parser.add_argument("--fp8_attention", action='store_true', default=True)
    parser.add_argument("--fp8_gemm", action='store_true', default=True)
    
    # S3 output (optional)
    parser.add_argument("--s3_bucket", type=str, default=os.environ.get('S3_OUTPUT_BUCKET', 'team11-data-source'),
                        help="S3 bucket for output (default: team11-data-source)")
    parser.add_argument("--s3_prefix", type=str, default="",
                        help="S3 prefix for output (default: auto-generated from theme)")
    
    args = parser.parse_args()
    
    # Verify input file exists
    panorama_path = os.path.join(args.input_dir, "panorama.png")
    if not os.path.exists(panorama_path):
        raise FileNotFoundError(f"Panorama not found: {panorama_path}")
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Copy panorama to output for reference
    shutil.copy(panorama_path, os.path.join(args.output_dir, "panorama.png"))
    
    # Initialize decomposer
    decomposer = PanoramaDecomposer(args)
    
    # Perform decomposition
    result = decomposer.decompose(
        panorama_path=panorama_path,
        labels_fg1=args.labels_fg1,
        labels_fg2=args.labels_fg2,
        classes=args.classes
    )
    
    # Save metadata
    metadata = {
        "labels_fg1": args.labels_fg1,
        "labels_fg2": args.labels_fg2,
        "classes": args.classes,
        "output_dir": args.output_dir
    }
    
    metadata_path = os.path.join(args.output_dir, "decomposition_metadata.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"[Step 2 Complete] Layers saved to: {args.output_dir}")
    print(f"[Output] Metadata: {metadata_path}")
    
    # Upload to S3 if specified
    if args.s3_bucket:
        s3_client = boto3.client('s3', region_name='ap-northeast-1')
        
        # Auto-generate prefix from theme if not specified
        s3_prefix = args.s3_prefix if args.s3_prefix else f"3dworlds/{args.theme}/layers/"
        
        print(f"[S3 Upload] Uploading layer data to s3://{args.s3_bucket}/{s3_prefix}")
        
        # Upload all files in output directory
        for root, dirs, files in os.walk(args.output_dir):
            for file in files:
                local_path = os.path.join(root, file)
                relative_path = os.path.relpath(local_path, args.output_dir)
                s3_key = f"{args.s3_prefix}{relative_path}"
                
                s3_client.upload_file(local_path, args.s3_bucket, s3_key)
                print(f"  - Uploaded: {relative_path}")
        
        print(f"[S3 Upload] Complete")
    
    # Memory cleanup
    del decomposer
    torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
