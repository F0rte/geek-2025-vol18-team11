#!/usr/bin/env python3
"""
Step Functions State Machine テストスクリプト
"""

import boto3
import json
import time
import argparse
from datetime import datetime

def start_execution(
    prompt: str,
    theme: str = None,
    classes: str = "outdoor",
    seed: int = 42,
    s3_bucket: str = "team11-data-source",
    ecr_image_uri: str = None,
    state_machine_arn: str = None,
    region: str = "us-east-1"
):
    """
    Start Step Functions execution
    
    Args:
        prompt: Text prompt
        theme: Theme name (auto-generated if not provided)
        classes: Scene classification
        seed: Random seed
        s3_bucket: S3 bucket
        ecr_image_uri: ECR image URI
        state_machine_arn: State Machine ARN
        region: AWS region
    """
    
    sfn = boto3.client('stepfunctions', region_name=region)
    sts = boto3.client('sts', region_name=region)
    
    # Auto-generate theme
    if not theme:
        import re
        theme = re.sub(r'[^a-z0-9]+', '_', prompt.lower())[:20].strip('_')
    
    # Get ECR image URI
    if not ecr_image_uri:
        account_id = sts.get_caller_identity()['Account']
        ecr_image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/team11-ai-engine-repo:latest"
    
    # Get State Machine ARN
    if not state_machine_arn:
        state_machine_arn = f"arn:aws:states:{region}:{sts.get_caller_identity()['Account']}:stateMachine:Team11AIEnginePipeline"
    
    # Execution ID
    execution_id = f"{theme}-{int(time.time())}"
    
    # Input parameters
    input_params = {
        "executionId": execution_id,
        "prompt": prompt,
        "theme": theme,
        "classes": classes,
        "seed": seed,
        "s3Bucket": s3_bucket,
        "ecrImageUri": ecr_image_uri
    }
    
    print("=" * 60)
    print("Starting Step Functions Execution")
    print("=" * 60)
    print(f"State Machine: {state_machine_arn}")
    print(f"Execution ID: {execution_id}")
    print(f"Prompt: {prompt}")
    print(f"Theme: {theme}")
    print(f"ECR Image: {ecr_image_uri}")
    print(f"S3 Bucket: {s3_bucket}")
    print("=" * 60)
    print()
    
    # Start execution
    response = sfn.start_execution(
        stateMachineArn=state_machine_arn,
        name=execution_id,
        input=json.dumps(input_params)
    )
    
    execution_arn = response['executionArn']
    print(f"✓ Execution started: {execution_arn}")
    print()
    
    # Monitor execution
    print("Monitoring execution status...")
    start_time = time.time()
    
    while True:
        exec_response = sfn.describe_execution(executionArn=execution_arn)
        status = exec_response['status']
        
        elapsed = time.time() - start_time
        print(f"[{elapsed/60:.1f} min] Status: {status}")
        
        if status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
            break
        
        time.sleep(30)
    
    elapsed_time = time.time() - start_time
    
    print()
    print("=" * 60)
    print("Execution Complete")
    print("=" * 60)
    print(f"Status: {status}")
    print(f"Elapsed Time: {elapsed_time/60:.2f} minutes")
    
    if status == 'SUCCEEDED':
        output = json.loads(exec_response.get('output', '{}'))
        print(f"Output: {json.dumps(output, indent=2)}")
        print()
        print(f"✓ Results available at: s3://{s3_bucket}/3dworlds/{theme}/")
    elif status == 'FAILED':
        error = exec_response.get('error', 'Unknown')
        cause = exec_response.get('cause', 'Unknown')
        print(f"✗ Error: {error}")
        print(f"  Cause: {cause}")
    
    print("=" * 60)
    
    # Cost estimate
    cost_g5_2xlarge = 1.515 * 2  # Step 1 + Step 2
    cost_g5_4xlarge = 2.03  # Step 3
    estimated_cost = (elapsed_time / 3600) * (cost_g5_2xlarge + cost_g5_4xlarge)
    print(f"Estimated Cost: ${estimated_cost:.4f}")
    
    return execution_arn, status


def main():
    parser = argparse.ArgumentParser(description="Test Step Functions State Machine")
    
    parser.add_argument("--prompt", type=str, required=True,
                        help="Text prompt for generation")
    parser.add_argument("--theme", type=str, default=None,
                        help="Theme name (auto-generated if not provided)")
    parser.add_argument("--classes", type=str, default="outdoor",
                        choices=["outdoor", "indoor"],
                        help="Scene classification")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed")
    parser.add_argument("--s3-bucket", type=str, default="team11-data-source",
                        help="S3 bucket")
    parser.add_argument("--ecr-image", type=str, default=None,
                        help="ECR image URI")
    parser.add_argument("--state-machine-arn", type=str, default=None,
                        help="State Machine ARN")
    parser.add_argument("--region", type=str, default="us-east-1",
                        help="AWS region")
    
    args = parser.parse_args()
    
    start_execution(
        prompt=args.prompt,
        theme=args.theme,
        classes=args.classes,
        seed=args.seed,
        s3_bucket=args.s3_bucket,
        ecr_image_uri=args.ecr_image,
        state_machine_arn=args.state_machine_arn,
        region=args.region
    )


if __name__ == "__main__":
    main()
