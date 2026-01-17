#!/usr/bin/env python3
"""
SageMaker Processing Job: Step 1 (Text to Panorama)
手動実行スクリプト
"""

import boto3
import time
import argparse
from sagemaker.processing import ScriptProcessor, ProcessingOutput

def run_step1(
    prompt: str,
    theme: str = "demo",
    instance_type: str = "ml.g5.2xlarge",
    role_arn: str = None,
    ecr_image_uri: str = None,
    s3_bucket: str = "team11-data-source",
    seed: int = 42,
    region: str = "us-east-1"
):
    """
    Run Step 1: Text to Panorama generation on SageMaker Processing Job
    
    Args:
        prompt: Text prompt for generation
        theme: Theme name for organizing outputs
        instance_type: SageMaker instance type (default: ml.g5.2xlarge)
        role_arn: SageMaker execution role ARN
        ecr_image_uri: ECR image URI for AI engine
        s3_bucket: S3 bucket for outputs
        seed: Random seed
        region: AWS region
    """
    
    # Initialize SageMaker session
    import sagemaker
    from sagemaker import get_execution_role
    
    session = sagemaker.Session(boto_session=boto3.Session(region_name=region))
    
    # Get role if not provided
    if not role_arn:
        try:
            role_arn = get_execution_role()
        except:
            raise ValueError("Please provide role_arn or run from SageMaker environment")
    
    # Get ECR image URI if not provided
    if not ecr_image_uri:
        account_id = boto3.client('sts', region_name=region).get_caller_identity()['Account']
        ecr_image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/team11-ai-engine-repo:latest"
    
    print(f"=== Step 1: Text to Panorama ===")
    print(f"Prompt: {prompt}")
    print(f"Theme: {theme}")
    print(f"Instance: {instance_type}")
    print(f"ECR Image: {ecr_image_uri}")
    print(f"S3 Bucket: {s3_bucket}")
    print(f"Region: {region}")
    print()
    
    # Create ScriptProcessor
    processor = ScriptProcessor(
        command=["python3"],
        image_uri=ecr_image_uri,
        role=role_arn,
        instance_count=1,
        instance_type=instance_type,
        volume_size_in_gb=50,
        max_runtime_in_seconds=3600,  # 60分
        base_job_name="step1-text2pano",
        sagemaker_session=session,
        env={
            'S3_OUTPUT_BUCKET': s3_bucket,
        }
    )
    
    # Output S3 path
    output_s3_uri = f"s3://{s3_bucket}/3dworlds/{theme}/"
    
    # Start processing job
    start_time = time.time()
    
    print(f"Starting Processing Job...")
    print(f"Output will be saved to: {output_s3_uri}")
    print()
    
    processor.run(
        code="src/step1_text2pano.py",
        source_dir="/opt/program",
        arguments=[
            "--prompt", prompt,
            "--theme", theme,
            "--seed", str(seed),
            "--s3_bucket", s3_bucket,
        ],
        outputs=[
            ProcessingOutput(
                output_name="panorama",
                source="/opt/ml/processing/output",
                destination=output_s3_uri
            )
        ],
        wait=True,
        logs=True
    )
    
    elapsed_time = time.time() - start_time
    
    print()
    print(f"=== Job Complete ===")
    print(f"Job Name: {processor.latest_job.name}")
    print(f"Elapsed Time: {elapsed_time/60:.2f} minutes")
    print(f"Output: {output_s3_uri}panorama.png")
    print()
    
    # Calculate cost (approximate)
    instance_cost_per_hour = {
        "ml.g5.2xlarge": 1.515,
        "ml.g5.4xlarge": 2.03,
        "ml.g4dn.xlarge": 0.736,
    }
    
    cost = (elapsed_time / 3600) * instance_cost_per_hour.get(instance_type, 1.0)
    print(f"Estimated Cost: ${cost:.4f}")
    
    return processor.latest_job.name, output_s3_uri


def main():
    parser = argparse.ArgumentParser(description="Run Step 1 on SageMaker")
    
    # Required
    parser.add_argument("--prompt", type=str, required=True,
                        help="Text prompt for generation")
    
    # Optional
    parser.add_argument("--theme", type=str, default="demo",
                        help="Theme name")
    parser.add_argument("--instance-type", type=str, default="ml.g5.2xlarge",
                        choices=["ml.g5.2xlarge", "ml.g5.4xlarge", "ml.g4dn.xlarge"],
                        help="SageMaker instance type")
    parser.add_argument("--role-arn", type=str, default=None,
                        help="SageMaker execution role ARN")
    parser.add_argument("--ecr-image", type=str, default=None,
                        help="ECR image URI")
    parser.add_argument("--s3-bucket", type=str, default="team11-data-source",
                        help="S3 bucket for outputs")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed")
    parser.add_argument("--region", type=str, default="us-east-1",
                        help="AWS region")
    
    args = parser.parse_args()
    
    run_step1(
        prompt=args.prompt,
        theme=args.theme,
        instance_type=args.instance_type,
        role_arn=args.role_arn,
        ecr_image_uri=args.ecr_image,
        s3_bucket=args.s3_bucket,
        seed=args.seed,
        region=args.region
    )


if __name__ == "__main__":
    main()
