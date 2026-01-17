#!/usr/bin/env python3
"""
SageMaker Processing Job: Step 1 (Text to Panorama)
手動実行スクリプト（boto3のみ使用）
"""

import boto3
import time
import argparse
import json

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
    
    # Initialize boto3 clients
    sagemaker = boto3.client('sagemaker', region_name=region)
    sts = boto3.client('sts', region_name=region)
    
    # Get ECR image URI if not provided
    if not ecr_image_uri:
        account_id = sts.get_caller_identity()['Account']
        ecr_image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/team11-ai-engine-repo:latest"
    
    # Validate role_arn
    if not role_arn:
        raise ValueError("Please provide --role-arn")
    
    print(f"=== Step 1: Text to Panorama ===")
    print(f"Prompt: {prompt}")
    print(f"Theme: {theme}")
    print(f"Instance: {instance_type}")
    print(f"ECR Image: {ecr_image_uri}")
    print(f"S3 Bucket: {s3_bucket}")
    print(f"Region: {region}")
    print()
    
    # Output S3 path
    output_s3_uri = f"s3://{s3_bucket}/3dworlds/{theme}/"
    
    # Job name
    job_name = f"step1-text2pano-{int(time.time())}"
    
    # Create Processing Job
    print(f"Starting Processing Job: {job_name}")
    print(f"Output will be saved to: {output_s3_uri}")
    print()
    
    start_time = time.time()
    
    sagemaker.create_processing_job(
        ProcessingJobName=job_name,
        RoleArn=role_arn,
        AppSpecification={
            'ImageUri': ecr_image_uri,
            'ContainerEntrypoint': [
                'python3',
                '/opt/program/src/step1_text2pano.py',
                '--prompt', prompt,
                '--theme', theme,
                '--seed', str(seed),
                '--s3_bucket', s3_bucket,
            ]
        },
        ProcessingResources={
            'ClusterConfig': {
                'InstanceCount': 1,
                'InstanceType': instance_type,
                'VolumeSizeInGB': 50
            }
        },
        ProcessingOutputConfig={
            'Outputs': [
                {
                    'OutputName': 'panorama',
                    'S3Output': {
                        'S3Uri': output_s3_uri,
                        'LocalPath': '/opt/ml/processing/output',
                        'S3UploadMode': 'EndOfJob'
                    }
                }
            ]
        },
        StoppingCondition={
            'MaxRuntimeInSeconds': 3600
        },
        Environment={
            'S3_OUTPUT_BUCKET': s3_bucket
        }
    )
    
    # Wait for job completion
    print("Waiting for job to complete...")
    while True:
        response = sagemaker.describe_processing_job(ProcessingJobName=job_name)
        status = response['ProcessingJobStatus']
        
        print(f"Status: {status}")
        
        if status in ['Completed', 'Failed', 'Stopped']:
            break
        
        time.sleep(30)
    
    elapsed_time = time.time() - start_time
    
    print()
    print(f"=== Job Complete ===")
    print(f"Job Name: {job_name}")
    print(f"Status: {status}")
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
    
    if status != 'Completed':
        failure_reason = response.get('FailureReason', 'Unknown')
        print(f"⚠️  Job failed: {failure_reason}")
        return None, None
    
    return job_name, output_s3_uri


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
