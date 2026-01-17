#!/usr/bin/env python3
"""
SageMaker Processing Job: All Steps (End-to-End Test)
3ステップを連続実行するスクリプト（boto3のみ使用）
"""

import argparse
import time
import sys
import os

# 同じディレクトリのモジュールをimport
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run_step1 import run_step1
from run_step2 import run_step2
from run_step3 import run_step3


def run_all_steps(
    prompt: str,
    theme: str = None,
    labels_fg1: list = None,
    labels_fg2: list = None,
    classes: str = "outdoor",
    role_arn: str = None,
    ecr_image_uri: str = None,
    s3_bucket: str = "team11-data-source",
    seed: int = 42,
    region: str = "us-east-1"
):
    """
    Run all 3 steps sequentially
    
    Args:
        prompt: Text prompt for generation
        theme: Theme name (auto-generated if not provided)
        labels_fg1: Foreground layer 1 labels
        labels_fg2: Foreground layer 2 labels
        classes: Scene classification
        role_arn: SageMaker execution role ARN
        ecr_image_uri: ECR image URI
        s3_bucket: S3 bucket
        seed: Random seed
        region: AWS region
    """
    
    # Auto-generate theme from prompt if not provided
    if not theme:
        import re
        theme = re.sub(r'[^a-z0-9]+', '_', prompt.lower())[:20].strip('_')
    
    labels_fg1 = labels_fg1 or []
    labels_fg2 = labels_fg2 or []
    
    print("=" * 60)
    print("End-to-End Test: All 3 Steps")
    print("=" * 60)
    print(f"Prompt: {prompt}")
    print(f"Theme: {theme}")
    print(f"FG1 Labels: {labels_fg1}")
    print(f"FG2 Labels: {labels_fg2}")
    print(f"S3 Bucket: {s3_bucket}")
    print("=" * 60)
    print()
    
    total_start_time = time.time()
    results = {}
    
    # Step 1: Text to Panorama
    print("\n" + "=" * 60)
    print("STEP 1: Text to Panorama")
    print("=" * 60)
    step1_job, step1_output = run_step1(
        prompt=prompt,
        theme=theme,
        instance_type="ml.g5.2xlarge",
        role_arn=role_arn,
        ecr_image_uri=ecr_image_uri,
        s3_bucket=s3_bucket,
        seed=seed,
        region=region
    )
    results['step1'] = {'job': step1_job, 'output': step1_output}
    
    # Step 2: Layer Decomposition
    print("\n" + "=" * 60)
    print("STEP 2: Layer Decomposition")
    print("=" * 60)
    step2_job, step2_output = run_step2(
        theme=theme,
        labels_fg1=labels_fg1,
        labels_fg2=labels_fg2,
        classes=classes,
        instance_type="ml.g5.2xlarge",
        role_arn=role_arn,
        ecr_image_uri=ecr_image_uri,
        s3_bucket=s3_bucket,
        region=region
    )
    results['step2'] = {'job': step2_job, 'output': step2_output}
    
    # Step 3: World Composition
    print("\n" + "=" * 60)
    print("STEP 3: World Composition")
    print("=" * 60)
    step3_job, step3_output = run_step3(
        theme=theme,
        instance_type="ml.g5.4xlarge",
        role_arn=role_arn,
        ecr_image_uri=ecr_image_uri,
        s3_bucket=s3_bucket,
        seed=seed,
        region=region
    )
    results['step3'] = {'job': step3_job, 'output': step3_output}
    
    total_elapsed_time = time.time() - total_start_time
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY: All Steps Complete")
    print("=" * 60)
    print(f"Total Execution Time: {total_elapsed_time/60:.2f} minutes")
    print()
    print("Job Names:")
    print(f"  Step 1: {results['step1']['job']}")
    print(f"  Step 2: {results['step2']['job']}")
    print(f"  Step 3: {results['step3']['job']}")
    print()
    print("Outputs:")
    print(f"  Panorama: {results['step1']['output']}panorama.png")
    print(f"  Layers:   {results['step2']['output']}")
    print(f"  Meshes:   {results['step3']['output']}")
    print()
    print(f"S3 Root: s3://{s3_bucket}/3dworlds/{theme}/")
    print("=" * 60)
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Run all 3 steps on SageMaker")
    
    # Required
    parser.add_argument("--prompt", type=str, required=True,
                        help="Text prompt for generation")
    
    # Optional
    parser.add_argument("--theme", type=str, default=None,
                        help="Theme name (auto-generated if not provided)")
    parser.add_argument("--labels-fg1", nargs='+', default=[],
                        help="Foreground layer 1 labels")
    parser.add_argument("--labels-fg2", nargs='+', default=[],
                        help="Foreground layer 2 labels")
    parser.add_argument("--classes", type=str, default="outdoor",
                        choices=["outdoor", "indoor"],
                        help="Scene classification")
    parser.add_argument("--role-arn", type=str, default=None,
                        help="SageMaker execution role ARN")
    parser.add_argument("--ecr-image", type=str, default=None,
                        help="ECR image URI")
    parser.add_argument("--s3-bucket", type=str, default="team11-data-source",
                        help="S3 bucket")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed")
    parser.add_argument("--region", type=str, default="us-east-1",
                        help="AWS region")
    
    args = parser.parse_args()
    
    run_all_steps(
        prompt=args.prompt,
        theme=args.theme,
        labels_fg1=args.labels_fg1,
        labels_fg2=args.labels_fg2,
        classes=args.classes,
        role_arn=args.role_arn,
        ecr_image_uri=args.ecr_image,
        s3_bucket=args.s3_bucket,
        seed=args.seed,
        region=args.region
    )


if __name__ == "__main__":
    main()
