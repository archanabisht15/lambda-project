import boto3
import os
import uuid
from PIL import Image
from io import BytesIO
from urllib.parse import unquote_plus
# These "clients" are how Python talks to AWS services.
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

# Fill these in with your actual resource names
PROCESSED_BUCKET = 'happy-processed-images-2026'
TABLE_NAME = 'happy-image-metadata'
SNS_TOPIC_ARN = 'arn:aws:sns:eu-north-1:864902168236:image-proccessed-notification'

table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    record = event['Records'][0]
    source_bucket = record['s3']['bucket']['name']
    file_key = unquote_plus(record['s3']['object']['key'])

    response = s3.get_object(Bucket=source_bucket, Key=file_key)
    image_bytes = response['Body'].read()

    image = Image.open(BytesIO(image_bytes))
    image.thumbnail((300, 300))

    buffer = BytesIO()
    image_format = image.format or 'JPEG'
    image.save(buffer, format=image_format)
    buffer.seek(0)

    new_key = f"resized-{file_key}"
    s3.put_object(Bucket=PROCESSED_BUCKET, Key=new_key, Body=buffer)

    table.put_item(Item={
        'image-id': str(uuid.uuid4()),
        'originalFile': file_key,
        'resizedFile': new_key,
        'sourceBucket': source_bucket
    })

    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject='Image processed',
        Message=f'{file_key} was resized and saved as {new_key}'
    )

    return {
        'statusCode': 200,
        'body': f'Successfully processed {file_key}'
    }
