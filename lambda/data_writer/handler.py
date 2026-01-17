import json
import os
import uuid
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
table_name = os.environ['DYNAMODB_TABLE_NAME']
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    """
    DynamoDBにメッシュメタデータを登録するLambda関数

    Expected event format:
    {
        "theme": "テーマ名",
        "png_uri": "s3://bucket/path/to/image.png",
        "ply_uris": [
            "s3://bucket/path/to/mesh1.ply",
            "s3://bucket/path/to/mesh2.ply",
            "s3://bucket/path/to/mesh3.ply",
            "s3://bucket/path/to/mesh4.ply"
        ]
    }
    """
    try:
        # イベントデータの取得
        theme = event.get('theme')
        png_uri = event.get('png_uri')
        ply_uris = event.get('ply_uris', [])

        # バリデーション
        if not theme:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'theme is required'})
            }

        if not png_uri:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'png_uri is required'})
            }

        if not ply_uris or len(ply_uris) < 3 or len(ply_uris) > 4:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'ply_uris must contain 3-4 URIs'})
            }

        # UUIDを自動生成
        item_id = str(uuid.uuid4())

        # DynamoDBアイテムの作成
        item = {
            'Id': item_id,
            'theme': theme,
            'png_uri': png_uri,
            'created_at': datetime.now(timezone.utc).isoformat()
        }

        # ply_urisを個別のカラムに展開
        for i, ply_uri in enumerate(ply_uris, start=1):
            item[f'ply_uri_{i}'] = ply_uri

        # DynamoDBに書き込み
        table.put_item(Item=item)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Successfully registered',
                'id': item_id,
                'item': item
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }
