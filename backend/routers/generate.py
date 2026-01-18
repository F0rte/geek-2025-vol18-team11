import os
import json
import time
import logging
import re
import boto3
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

# Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# AWS clients
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
sfn = boto3.client('stepfunctions', region_name='us-east-1')
sts = boto3.client('sts', region_name='us-east-1')

# Environment variables
STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN', '')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'team11-data-source')


class GenerateRequest(BaseModel):
    prompt_ja: str = Field(..., max_length=500, description="日本語プロンプト（500文字以内）")
    seed: int = Field(default=42, description="ランダムシード")
    classes: str = Field(default="outdoor", description="シーン分類")


class GenerateResponse(BaseModel):
    execution_arn: str
    execution_id: str
    theme: str
    prompt_en: str
    status: str


class StatusResponse(BaseModel):
    execution_arn: str
    status: str
    output: dict = None
    error: str = None


@router.post("/generate", response_model=GenerateResponse)
def generate_world(request: GenerateRequest):
    """mock"""
    # ============================================================================
    # MOCK VERSION - 本番環境用の実装はコメントアウトされています
    # ============================================================================
    try:
        logger.info(f"[MOCK] Generating mock response for: {request.prompt_ja}")
        
        # モック用のテーマ生成（日本語プロンプトから簡単に生成）
        theme = "mock-world"
        if len(request.prompt_ja) > 0:
            # 最初の数文字をテーマに含める（英数字のみ）
            clean_prompt = re.sub(r'[^a-zA-Z0-9]', '', request.prompt_ja[:10])
            if clean_prompt:
                theme = f"mock-{clean_prompt.lower()}"
        
        # モック用の英語プロンプト
        prompt_en = f"A beautiful 3D world based on: {request.prompt_ja}"
        
        # モック用のexecution_id（ARNっぽくない形式）
        timestamp = int(time.time())
        execution_id = f"mock-{timestamp}"
        execution_arn = f"mock-execution-{timestamp}"
        
        logger.info(f"[MOCK] Generated - theme: {theme}, execution_id: {execution_id}")
        
        return GenerateResponse(
            execution_arn=execution_arn,
            execution_id=execution_id,
            theme=theme,
            prompt_en=prompt_en,
            status="RUNNING"
        )
        
    except Exception as e:
        logger.error(f"Error generating mock world: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
    # ============================================================================
    # 本番環境用実装（コメントアウト）
    # ============================================================================
    # try:
    #     # Step 1: Bedrock呼び出しで英語プロンプトとテーマ生成
    #     logger.info(f"Generating theme and English prompt from: {request.prompt_ja}")
    #     
    #     bedrock_prompt = f"""以下の日本語プロンプトから、3Dワールド生成用の英語テーマ名とプロンプトを生成してください。
    #
    # 日本語プロンプト: {request.prompt_ja}
    #
    # 以下のJSON形式で出力してください:
    # {{
    #   "theme": "簡潔な英語テーマ名（ハイフン区切り、10文字以内、英数字とハイフンのみ使用）",
    #   "prompt_en": "詳細な英語プロンプト（HunyuanWorld用）"
    # }}
    #
    # JSONのみを出力し、他の説明は不要です。"""
    #
    #     bedrock_body = {
    #         "messages": [
    #             {
    #                 "role": "user",
    #                 "content": [
    #                     {
    #                         "text": bedrock_prompt
    #                     }
    #                 ]
    #             }
    #         ],
    #         "inferenceConfig": {
    #             "max_new_tokens": 200,
    #             "temperature": 0.7
    #         }
    #     }
    #     
    #     response = bedrock.invoke_model(
    #         modelId="amazon.nova-micro-v1:0",
    #         body=json.dumps(bedrock_body)
    #     )
    #     
    #     response_body = json.loads(response['body'].read())
    #     content = response_body['output']['message']['content'][0]['text']
    #     
    #     # JSON部分を抽出
    #     json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
    #     if not json_match:
    #         raise ValueError(f"Bedrock response does not contain valid JSON: {content}")
    #     
    #     result = json.loads(json_match.group())
    #     theme = result.get('theme', '').strip()
    #     prompt_en = result.get('prompt_en', '').strip()
    #     
    #     if not theme or not prompt_en:
    #         raise ValueError(f"Invalid Bedrock response: {result}")
    #     
    #     # テーマ名をSageMaker ProcessingJob名に適合させる（英数字とハイフンのみ）
    #     theme = re.sub(r'[^a-zA-Z0-9-]', '-', theme)
    #     theme = re.sub(r'-+', '-', theme).strip('-')  # 連続ハイフンを1つに、前後のハイフンを削除
    #     
    #     logger.info(f"Generated theme: {theme}, prompt_en: {prompt_en}")
    #     
    #     # Step 2: Step Functions起動
    #     account_id = sts.get_caller_identity()['Account']
    #     ecr_image_uri = f"{account_id}.dkr.ecr.us-east-1.amazonaws.com/team11-ai-engine-repo:latest"
    #     execution_id = f"{theme}-{int(time.time())}"
    #     
    #     input_params = {
    #         "executionId": execution_id,
    #         "prompt": prompt_en,
    #         "theme": theme,
    #         "theme_ja": request.prompt_ja,
    #         "classes": request.classes,
    #         "seed": request.seed,
    #         "s3Bucket": S3_BUCKET_NAME,
    #         "ecrImageUri": ecr_image_uri
    #     }
    #     
    #     logger.info(f"Starting Step Functions execution: {execution_id}")
    #     
    #     sfn_response = sfn.start_execution(
    #         stateMachineArn=STATE_MACHINE_ARN,
    #         name=execution_id,
    #         input=json.dumps(input_params)
    #     )
    #     
    #     execution_arn = sfn_response['executionArn']
    #     
    #     logger.info(f"Step Functions execution started: {execution_arn}")
    #     
    #     return GenerateResponse(
    #         execution_arn=execution_arn,
    #         execution_id=execution_id,
    #         theme=theme,
    #         prompt_en=prompt_en,
    #         status="RUNNING"
    #     )
    #     
    # except Exception as e:
    #     logger.error(f"Error generating world: {e}", exc_info=True)
    #     raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{execution_id}", response_model=StatusResponse)
def get_generation_status(execution_id: str):
    """mock"""
    # ============================================================================
    # MOCK VERSION - 本番環境用の実装はコメントアウトされています
    # ============================================================================
    try:
        logger.info(f"[MOCK] Checking execution status: {execution_id}")
        
        # モック用のexecution_arn
        execution_arn = f"mock-execution-{execution_id.replace('mock-', '')}"
        
        # モックレスポンス（常にSUCCEEDED）
        result = {
            "execution_arn": execution_arn,
            "status": "SUCCEEDED",
            "output": {
                "theme": "mock-world",
                "message": "Mock execution completed successfully"
            }
        }
        
        return StatusResponse(**result)
        
    except Exception as e:
        logger.error(f"Error fetching mock execution status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
    # ============================================================================
    # 本番環境用実装（コメントアウト）
    # ============================================================================
    # try:
    #     # execution_id から execution_arn を構築
    #     account_id = sts.get_caller_identity()['Account']
    #     execution_arn = f"arn:aws:states:us-east-1:{account_id}:execution:Team11AIEnginePipeline:{execution_id}"
    #     
    #     logger.info(f"Checking execution status: {execution_arn}")
    #     
    #     response = sfn.describe_execution(executionArn=execution_arn)
    #     
    #     status = response['status']
    #     result = {
    #         "execution_arn": execution_arn,
    #         "status": status
    #     }
    #     
    #     if status == 'SUCCEEDED':
    #         output = json.loads(response.get('output', '{}'))
    #         result['output'] = output
    #     elif status == 'FAILED':
    #         result['error'] = response.get('error', 'Unknown error')
    #     
    #     return StatusResponse(**result)
    #     
    # except sfn.exceptions.ExecutionDoesNotExist:
    #     raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
    # except Exception as e:
    #     logger.error(f"Error fetching execution status: {e}", exc_info=True)
    #     raise HTTPException(status_code=500, detail=str(e))
