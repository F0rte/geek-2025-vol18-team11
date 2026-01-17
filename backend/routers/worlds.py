import os
import logging
import boto3
from fastapi import APIRouter, HTTPException

router = APIRouter()

# Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# AWS clients
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')

# Environment variables
DYNAMODB_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', '')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', '')

@router.get("/worlds")
def get_worlds():
    """
    DynamoDBから生成済み3DWorldの一覧を取得し、S3 URIをPresigned URLに変換して返す
    """
    try:
        # DynamoDBテーブルから全アイテムを取得
        table = dynamodb.Table(DYNAMODB_TABLE_NAME)
        response = table.scan()
        items = response.get('Items', [])
        
        worlds = []
        for item in items:
            # Presigned URLを生成（有効期限: 600秒）
            png_url = generate_presigned_url(item.get('png_uri', ''))
            
            ply_urls = []
            for i in range(1, 5):  # ply_uri_1 ~ ply_uri_4
                ply_uri = item.get(f'ply_uri_{i}')
                if ply_uri:
                    ply_urls.append(generate_presigned_url(ply_uri))
            
            worlds.append({
                'id': item.get('Id'),
                'theme': item.get('theme'),
                'png_url': png_url,
                'ply_urls': ply_urls,
                'created_at': item.get('created_at')
            })
        
        return {'worlds': worlds}
    
    except Exception as e:
        logger.error(f"Error fetching worlds: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

def generate_presigned_url(s3_uri: str, expiration: int = 600) -> str:
    """
    S3 URIからPresigned URLを生成
    
    Args:
        s3_uri: S3 URI (e.g., s3://bucket/key)
        expiration: URL有効期限（秒）
    
    Returns:
        Presigned URL
    """
    if not s3_uri or not s3_uri.startswith('s3://'):
        return ''
    
    # s3://bucket/key から bucket と key を抽出
    parts = s3_uri.replace('s3://', '').split('/', 1)
    if len(parts) != 2:
        return ''
    
    bucket = parts[0]
    key = parts[1]
    
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expiration
        )
        return url
    except Exception as e:
        logger.error(f"Error generating presigned URL for {s3_uri}: {e}")
        return ''
