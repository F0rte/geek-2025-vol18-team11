#!/usr/bin/env python3
"""
SageMaker Processing Job: Step 2 (Layer Decomposition)
手動実行スクリプト
"""

import boto3
import time
import argparse
from sagemaker.processing import ScriptProcessor, ProcessingInput, ProcessingOutput

def run_step2(
    theme: str = "demo",
    labels_fg1: list = None,
    labels_fg2: list = None,
    classes: str = "outdoor",
    instance_type: str = "ml.g5.2xlarge",
    role_arn: str = None,
    ecr_image_uri: str = None,
    s3_bucket: str = "team11-data-source",
    region: str = "us-east-1"
):
    """
    Run Step 2: Layer Decomposition on SageMaker Processing Job
    
    Args:
        theme: Theme name (must match Step 1 output)
        labels_fg1: Foreground layer 1 labels
        labels_fg2: Foreground layer 2 labels
        classes: Scene classification (outdoor/indoor)
        instance_type: SageMaker instance type
        role_arn: SageMaker execution role ARN
        ecr_image_uri: ECR image URI
        s3_bucket: S3 bucket
        region: AWS region
    """
    
    import sagemaker
    from sagemaker import get_execution_role
    
    session = sagemaker.Session(boto_session=boto3.Session(region_name=region))
    
    if not role_arn:
        try:
            role_arn = get_execution_role()
        except:
            raise ValueError("Please provide role_arn or run from SageMaker environment")
    
    if not ecr_image_uri:
        account_id = boto3.client('sts', region_name=region).get_caller_identity()['Account']
        ecr_image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/team11-ai-engine-repo:latest"
    
    labels_fg1 = labels_fg1 or []
    labels_fg2 = labels_fg2 or []
    
    print(f"=== Step 2: Layer Decomposition ===")
    print(f"Theme: {theme}")
    print(f"FG1 Labels: {labels_fg1}")
    print(f"FG2 Labels: {labels_fg2}")
    print(f"Classes: {classes}")
    print(f"Instance: {instance_type}")
    print()
    
    # Input/Output S3 paths
    input_s3_uri = f"s3://{s3_bucket}/3dworlds/{theme}/"
    output_s3_uri = f"s3://{s3_bucket}/3dworlds/{theme}/layers/"
    
    # Create ScriptProcessor
    processor = ScriptProcessor(
        command=["python3"],
        image_uri=ecr_image_uri,
        role=role_arn,
        instance_count=1,
        instance_type=instance_type,
        volume_size_in_gb=50,
        max_runtime_in_seconds=1800,  # 30分
        base_job_name="step2-decompose",
        sagemaker_session=session,
        env={
            'S3_OUTPUT_BUCKET': s3_bucket,
        }
    )
    
    # Build arguments
    arguments = [
        "--theme", theme,
        "--classes", classes,
        "--s3_bucket", s3_bucket,
    ]
    
    if labels_fg1:
        arguments.extend(["--labels_fg1"] + labels_fg1)
    if labels_fg2:
        arguments.extend(["--labels_fg2"] + labels_fg2)
    
    # Start processing job
    start_time = time.time()
    
    print(f"Starting Processing Job...")
    print(f"Input: {input_s3_uri}")
    print(f"Output: {output_s3_uri}")
    print()
    
    processor.run(
        code="src/step2_decompose.py",
        source_dir="/opt/program",
        arguments=arguments,
        inputs=[
            ProcessingInput(
                input_name="panorama",
                source=input_s3_uri,
                destination="/opt/ml/processing/input"
            )
        ],
        outputs=[
            ProcessingOutput(
                output_name="layers",
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
    print(f"Output: {output_s3_uri}")
    
    instance_cost_per_hour = {
        "ml.g5.2xlarge": 1.515,
        "ml.g5.4xlarge": 2.03,
    }
    cost = (elapsed_time / 3600) * instance_cost_per_hour.get(instance_type, 1.5)
    print(f"Estimated Cost: ${cost:.4f}")
    
    return processor.latest_job.name, output_s3_uri


def main():
    parser = argparse.ArgumentParser(description="Run Step 2 on SageMaker")
    
    parser.add_argument("--theme", type=str, default="demo",
                        help="Theme name (must match Step 1)")
    parser.add_argument("--labels-fg1", nargs='+', default=[],
                        help="Foreground layer 1 labels")
    parser.add_argument("--labels-fg2", nargs='+', default=[],
                        help="Foreground layer 2 labels")
    parser.add_argument("--classes", type=str, default="outdoor",
                        choices=["outdoor", "indoor"],
                        help="Scene classification")
    parser.add_argument("--instance-type", type=str, default="ml.g5.2xlarge",
                        help="SageMaker instance type")
    parser.add_argument("--role-arn", type=str, default=None,
                        help="SageMaker execution role ARN")
    parser.add_argument("--ecr-image", type=str, default=None,
                        help="ECR image URI")
    parser.add_argument("--s3-bucket", type=str, default="team11-data-source",
                        help="S3 bucket")
    parser.add_argument("--region", type=str, default="us-east-1",
                        help="AWS region")
    
    args = parser.parse_args()
    
    run_step2(
        theme=args.theme,
        labels_fg1=args.labels_fg1,
        labels_fg2=args.labels_fg2,
        classes=args.classes,
        instance_type=args.instance_type,
        role_arn=args.role_arn,
        ecr_image_uri=args.ecr_image,
        s3_bucket=args.s3_bucket,
        region=args.region
    )


if __name__ == "__main__":
    main()
