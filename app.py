import os
import boto3
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
# Importing the RAGEngine which handles the Kaggle ingestion and Bedrock calls
from rag_engine import RAGEngine

# Load the variables from the .env file
load_dotenv()

app = Flask(__name__)

# ==============================================================
# 🔒 AWS CONFIGURATION (from .env)
# ==============================================================
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1") # Defaults to us-east-1 if missing
# ==============================================================

# Initialize the Boto3 S3 client
s3_client = boto3.client('s3', region_name=AWS_REGION)

# 1. ONLY ONE Tracker Dictionary
job_tracker = {}

print("[*] Starting Web Server...")
print("[*] Initializing RAG Engine (Processing Kaggle Dataset)...")
print("[!] Note: This may take a few minutes for Bedrock to generate embeddings. Wait for the 'Running' message.")

# Initialize the engine and run the ingestion logic
rag = RAGEngine()
rag.download_and_ingest_kaggle()

@app.route('/')
def index():
    """Serves the central agent page with the green environment UI."""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """HANDLES FILE UPLOAD: Streams it directly to your S3 Bucket."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        filename = secure_filename(file.filename)
        s3_client.upload_fileobj(file, S3_BUCKET_NAME, filename)

        # Pre-load the tracker so the UI immediately sees it's waiting
        job_tracker[filename] = "Waiting for worker to start..."

        # 🚀 ONLY CHANGE: Added "filename": filename to the response!
        return jsonify({
            "message": f"Successfully uploaded {filename} to S3. Agent is learning...",
            "filename": filename
        }), 200
    except Exception as e:
        return jsonify({"error": f"S3 Upload Failed: {str(e)}"}), 500

# 2. ONLY ONE Webhook Route for the Worker
@app.route('/webhook/status', methods=['POST'])
def update_status():
    """Single endpoint for worker.py to send all progress updates."""
    data = request.json
    filename = data.get('filename')
    message = data.get('message')

    if filename:
        job_tracker[filename] = message
        print(f"[TRACKER UPDATE] {filename}: {message}")
        return jsonify({"status": "success"}), 200

    return jsonify({"status": "error", "message": "No filename provided"}), 400


# 3. ONLY ONE Status API Route for the Web UI
@app.route('/api/status/<path:filename>', methods=['GET'])
def get_status(filename):
    """Endpoint for the browser UI to check the file's current progress."""
    status = job_tracker.get(filename, "Waiting for processor...")
    return jsonify({"filename": filename, "status": status})


@app.route('/ask', methods=['POST'])
def ask():
    """HANDLES QUESTIONS: Calls the rag_engine to get an answer from Claude."""
    data = request.json
    question = data.get('question')

    if not question:
        return jsonify({"error": "No question provided"}), 400

    try:
        answer = rag.ask_question(question)
        return jsonify({"answer": answer}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to generate answer: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)