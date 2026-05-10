import os
import time
import json
import boto3
import urllib.parse
import requests
from dotenv import load_dotenv
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

# Load the variables from the .env file
load_dotenv()

# ==============================================================
# ⚠️ AWS CONFIGURATION - CHANGE THESE TO MATCH YOUR CONSOLE
# ==============================================================
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
# Keeping your specific Queue URL
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")
# REPLACE THIS WITH YOUR ACTUAL AOSS ENDPOINT (Do not include https://)
OPENSEARCH_ENDPOINT = os.getenv("OPENSEARCH_ENDPOINT")
# ==============================================================

print("[*] Initializing Enterprise Background Worker...")

# Initialize Standard AWS Clients
sqs_client = boto3.client('sqs', region_name=AWS_REGION)
s3_client = boto3.client('s3', region_name=AWS_REGION)
bedrock_client = boto3.client('bedrock-runtime', region_name=AWS_REGION)

# Initialize OpenSearch Client
credentials = boto3.Session().get_credentials()
auth = AWSV4SignerAuth(credentials, AWS_REGION, 'aoss')

os_client = OpenSearch(
    hosts=[{'host': OPENSEARCH_ENDPOINT, 'port': 443}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
)

# The URL of your Flask web app
WEB_APP_URL = "http://localhost:5000/webhook/status"

def send_notification(filename, message):
    """Sends a progress update back to the main web UI."""
    try:
        requests.post(WEB_APP_URL, json={
            "filename": filename,
            "message": message
        }, timeout=3)
    except Exception as e:
        print(f"[!] Could not send notification to web app: {e}")


def get_titan_embedding(text):
    """Calls AWS Bedrock to convert text into a 1536-dimension vector."""
    try:
        body = json.dumps({"inputText": text})
        response = bedrock_client.invoke_model(
            body=body,
            modelId='amazon.titan-embed-text-v1',
            accept='application/json',
            contentType='application/json'
        )
        response_body = json.loads(response.get('body').read())
        return response_body.get('embedding')
    except Exception as e:
        print(f"[!] Embedding Error: {e}")
        return None

def process_document(bucket_name, object_key):
    """Downloads the file from S3, chunks it, and pushes it to OpenSearch with progress notifications."""

    # 📢 Milestone 1: Worker has started the job
    send_notification(object_key, "📥 Worker received file. Starting download from S3...")
    print(f"\n[*] Downloading {object_key} from S3 bucket {bucket_name}...")

    # Handle local pathing
    local_filename = os.path.basename(object_key)
    local_path = local_filename

    try:
        s3_client.download_file(bucket_name, object_key, local_path)
        # 📢 Milestone 2: S3 Transfer Success
        send_notification(object_key, "✅ S3 Download complete. Parsing text...")
    except Exception as e:
        error_msg = f"❌ S3 Download Failed: {str(e)}"
        send_notification(object_key, error_msg)
        print(f"[!] {error_msg}")
        return

    # Read the file
    try:
        with open(local_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        error_msg = f"❌ File Read Error: {str(e)}"
        send_notification(object_key, error_msg)
        return

    # Chunking
    chunks = [content[i:i + 1000] for i in range(0, len(content), 1000)]
    # 📢 Milestone 3: Document sliced
    send_notification(object_key, f"🔪 Document sliced into {len(chunks)} chunks. Beginning AI embedding...")
    print(f"[*] Sliced document into {len(chunks)} chunks. Generating embeddings...")

    success_count = 0
    for i, chunk in enumerate(chunks):
        # 🚀 ADDED DIAGNOSTIC: See exactly what text is being sent to Bedrock
        print(f"    [DEBUG] Text inside chunk: '{chunk}'")

        vector = get_titan_embedding(chunk)

        if not vector:
            # 🚀 ADDED DIAGNOSTIC: Catch Bedrock silent failures
            print(f"    [!] FAILED: Bedrock refused to generate math for this text.")
        else:
            # 🚀 ADDED DIAGNOSTIC: Confirm Bedrock success
            print(f"    [DEBUG] Bedrock success! Vector size: {len(vector)}")

            document = {
                "text": chunk,
                "embedding": vector
            }
            try:
                # 🚀 PUSH TO OPENSEARCH
                os_client.index(index="happiness-index", body=document)
                success_count += 1

                print(f"    -> Embedded and saved chunk {i + 1}/{len(chunks)} to OpenSearch")

                # Update UI every 5 chunks to show it's alive
                if (i + 1) % 5 == 0:
                    send_notification(object_key, f"🧠 Progress: Indexed {i + 1}/{len(chunks)} chunks...")

            except Exception as e:
                print(f"    [!] OpenSearch Save Error: {e}")

    # Clean up the temporary file
    if os.path.exists(local_path):
        os.remove(local_path)

    # 📢 Milestone 4: Complete
    final_status = f"🚀 Success! {success_count}/{len(chunks)} chunks are now in the RAG vault."
    send_notification(object_key, final_status)
    print(f"[✓] Successfully processed: {object_key}")


def poll_queue():
    """Infinite loop that constantly checks SQS for new file notifications."""
    print("[*] Worker is running and listening for S3 uploads via SQS...\n")

    while True:
        try:
            # Check the queue for new messages (Wait up to 20 seconds - "Long Polling")
            response = sqs_client.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20
            )

            if 'Messages' in response:
                for message in response['Messages']:
                    receipt_handle = message['ReceiptHandle']
                    body = json.loads(message['Body'])

                    # Extract S3 bucket and filename from the SQS event notification
                    if 'Records' in body:
                        for record in body['Records']:
                            bucket_name = record['s3']['bucket']['name']

                            # 🚀 THIS IS THE FIX FOR FILENAMES WITH SPACES:
                            raw_key = record['s3']['object']['key']
                            object_key = urllib.parse.unquote_plus(raw_key)

                            # Do the heavy lifting
                            process_document(bucket_name, object_key)

                    # Delete the message from the queue so we don't process it twice
                    sqs_client.delete_message(
                        QueueUrl=SQS_QUEUE_URL,
                        ReceiptHandle=receipt_handle
                    )
            else:
                pass

        except Exception as e:
            print(f"[!] Worker Error: {str(e)}")
            time.sleep(5)


if __name__ == '__main__':
    poll_queue()