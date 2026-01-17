#!/usr/bin/env python3
"""
SageMaker Processing Job: Step 3 (World Composition)
手動実行スクリプト（boto3のみ使用）
"""

import boto3
import time
import argparse

def run_step3(
    theme: str = "demo",
    instance_type: str = "ml.g5.4xlarge",  # 高解像度のため4xlarge推奨
    role_arn: str = None,
    ecr_image_uri: str = None,
    s3_bucket: str = "team11-data-source",
    seed: int = 42,
    export_drc: bool = False,
    region: str = "us-east-1"
):
    """
    Run Step 3: World Composition on SageMaker Processing Job
    
    Args:
        theme: Theme name (must match previous steps)
        instance_type: SageMaker instance type (ml.g5.4xlarge recommended)
        role_arn: SageMaker execution role ARN
        ecr_image_uri: ECR image URI
        s3_bucket: S3 bucket
        seed: Random seed
        export_drc: Export Draco compressed format
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
    
    print(f"=== Step 3: World Composition ===")
    print(f"Theme: {theme}")
    print(f"Instance: {instance_type}")
    print(f"Export DRC: {export_drc}")
    print()
    
    # Input/Output S3 paths
    input_s3_uri = f"s3://{s3_bucket}/3dworlds/{theme}/layers/"
    output_s3_uri = f"s3://{s3_bucket}/3dworlds/{theme}/"
    
    # Job name
    job_name = f"step3-compose-{int(time.time())}"
    
    # Build arguments
    container_args = [
        'python3',
        '/opt/program/src/step3_compose.py',
        '--theme', theme,
        '--seed', str(seed),
        '--s3_bucket', s3_bucket,
    ]
    
    if export_drc:
        container_args.append('--export_drc')
    
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
                'VolumeSizeInGB': 100
            }
        },
        ProcessingInputs=[
            {
                'InputName': 'layers',
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
                    'OutputName': 'meshes',
                    'S3Output': {
                        'S3Uri': output_s3_uri,
                        'LocalPath': '/opt/ml/processing/output',
                        'S3UploadMode': 'EndOfJob'
                    }
                }
            ]
        },
        StoppingCondition={
            'MaxRuntimeInSeconds': 2400
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
    cost = (elapsed_time / 3600) * instance_cost_per_hour.get(instance_type, 2.0)
    print(f"Estimated Cost: ${cost:.4f}")
    
    if status != 'Completed':
        failure_reason = response.get('FailureReason', 'Unknown')
        print(f"⚠️  Job failed: {failure_reason}")
        return None, None
    
    return job_name, output_s3_uri


def main():
    parser = argparse.ArgumentParser(description="Run Step 3 on SageMaker")
    
    parser.add_argument("--theme", type=str, default="demo",
                        help="Theme name (must match previous steps)")
    parser.add_argument("--instance-type", type=str, default="ml.g5.4xlarge",
                        help="SageMaker instance type")
    parser.add_argument("--role-arn", type=str, default=None,
                        help="SageMaker execution role ARN")
    parser.add_argument("--ecr-image", type=str, default=None,
                        help="ECR image URI")
    parser.add_argument("--s3-bucket", type=str, default="team11-data-source",
                        help="S3 bucket")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed")
    parser.add_argument("--export-drc", action='store_true',
                        help="Export Draco compressed format")
    parser.add_argument("--region", type=str, default="us-east-1",
                        help="AWS region")
    
    args = parser.parse_args()
    
    run_step3(
        theme=args.theme,
        instance_type=args.instance_type,
        role_arn=args.role_arn,
        ecr_image_uri=args.ecr_image,
        s3_bucket=args.s3_bucket,
        seed=args.seed,
        export_drc=args.export_drc,
        region=args.region
    )


if __name__ == "__main__":
    main()
