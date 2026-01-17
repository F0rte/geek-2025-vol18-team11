#!/usr/bin/env python3
"""
SageMaker Processing Job: Step 2 (Layer Decomposition)
手動実行スクリプト（boto3のみ使用）
"""

import boto3
import time
import argparse

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
    
    # Initialize boto3 clients
    sagemaker = boto3.client('sagemaker', region_name=region)
    sts = boto3.client('sts', region_name=region)
    
    if not ecr_image_uri:
        account_id = sts.get_caller_identity()['Account']
        ecr_image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/team11-ai-engine-repo:latest"
    
    if not role_arn:
        raise ValueError("Please provide --role-arn")
    
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
    
    # Job name
    job_name = f"step2-decompose-{int(time.time())}"
    
    # Build arguments
    container_args = [
        'python3',
        '/opt/program/src/step2_decompose.py',
        '--theme', theme,
        '--classes', classes,
        '--s3_bucket', s3_bucket,
    ]
    
    if labels_fg1:
        container_args.extend(['--labels_fg1'] + labels_fg1)
    if labels_fg2:
        container_args.extend(['--labels_fg2'] + labels_fg2)
    
    # Start processing job
    start_time = time.time()
    
    print(f"Starting Processing Job: {job_name}")
    print(f"Input: {input_s3_uri}")
    print(f"Output: {output_s3_uri}")
    print()
    
    sagemaker.create_processing_job(
        ProcessingJobName=job_name,
        RoleArn=role_arn,
        AppSpecification={
            'ImageUri': ecr_image_uri,
            'ContainerEntrypoint': container_args
        },
        ProcessingResources={
            'ClusterConfig': {
                'InstanceCount': 1,
                'InstanceType': instance_type,
                'VolumeSizeInGB': 50
            }
        },
        ProcessingInputs=[
            {
                'InputName': 'panorama',
                'S3Input': {
                    'S3Uri': input_s3_uri,
                    'LocalPath': '/opt/ml/processing/input',
                    'S3DataType': 'S3Prefix',
                    'S3InputMode': 'File'
                }
            }
        ],
        ProcessingOutputConfig={
            'Outputs': [
                {
                    'OutputName': 'layers',
                    'S3Output': {
                        'S3Uri': output_s3_uri,
                        'LocalPath': '/opt/ml/processing/output',
                        'S3UploadMode': 'EndOfJob'
                    }
                }
            ]
        },
        StoppingCondition={
            'MaxRuntimeInSeconds': 1800
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
    print(f"Output: {output_s3_uri}")
    
    instance_cost_per_hour = {
        "ml.g5.2xlarge": 1.515,
        "ml.g5.4xlarge": 2.03,
    }
    cost = (elapsed_time / 3600) * instance_cost_per_hour.get(instance_type, 1.5)
    print(f"Estimated Cost: ${cost:.4f}")
    
    if status != 'Completed':
        failure_reason = response.get('FailureReason', 'Unknown')
        print(f"⚠️  Job failed: {failure_reason}")
        return None, None
    
    return job_name, output_s3_uri


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
