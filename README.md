# Enterprise Event-Driven RAG Architecture

A fully decoupled, scalable Retrieval-Augmented Generation (RAG) application. This project features a responsive web UI that communicates asynchronously with a background Python worker via AWS SQS to ingest, embed, and store documents in a vector database for real-time querying by an AI agent.

## 🎯 Project Goal
Traditional RAG applications often freeze the user interface while processing heavy documents. This project solves that by decoupling the web server from the AI processing engine. When a user uploads a file, it is securely stored in AWS S3. An event notification wakes up a background worker via SQS, which downloads the file, chunks the text, generates vector embeddings using Amazon Bedrock, and indexes them into OpenSearch—all while providing real-time HTTP webhook updates back to the UI.

## 🚀 Architecture & Flow
1. **Frontend UI:** A glassmorphism chat interface handles file uploads and user queries.
2. **Cloud Vault (Amazon S3):** Acts as the secure, immutable storage for uploaded documents.
3. **Message Broker (Amazon SQS):** Decouples the web server from the background processor, handling S3 event notifications.
4. **Background Worker:** A Python script that listens to SQS, downloads files, chunks text, and generates 1536-dimensional vectors using **Amazon Titan Embeddings**.
5. **Vector Database (Amazon OpenSearch Serverless):** Stores the text embeddings and performs blazing-fast K-Nearest Neighbor (k-NN) similarity searches.
6. **LLM Engine (Claude 3 on Bedrock):** Uses the retrieved context from OpenSearch to generate strictly grounded answers, eliminating AI hallucination.

## 🛠️ Technology Stack
* **Backend:** Python, Flask, Werkzeug
* **AWS Infrastructure:** S3, SQS, OpenSearch Serverless, Bedrock
* **AI Models:** Anthropic Claude 3 (Generation), Amazon Titan (Embeddings)
* **Frontend:** HTML5, CSS3, Vanilla JavaScript

'## 📝 Important Notes
* **Data Privacy:** All documents uploaded to the vault remain private to your AWS account. OpenSearch Serverless data is encrypted at rest.
* **Cost Warning:** Running Amazon Bedrock and OpenSearch Serverless will incur AWS charges. Be sure to tear down your infrastructure when not testing to avoid unexpected bills.

## ⚙️ Quick Start Guide
1. AWS Prerequisites
Before running this application, you must have the following configured in your AWS account:
Model Access: Amazon Titan Text Embeddings V2 and Anthropic Claude 3 enabled in AWS Bedrock.
S3 Bucket: An S3 bucket configured with Event Notifications sending s3:ObjectCreated:* events to an SQS queue.
SQS Queue: A standard SQS queue with an Access Policy allowing your S3 bucket to send messages to it.
OpenSearch Serverless: A vector search collection with Data Access Policies granting read/write permissions to your IAM user.

2. Local Installation
Clone the repository and install the required dependencies:

Bash
git clone [https://github.com/YOUR_USERNAME/enterprise-rag-agent.git](https://github.com/YOUR_USERNAME/enterprise-rag-agent.git)
cd enterprise-rag-agent
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
3. Environment Configuration
Create a .env file in the root directory and add your specific AWS infrastructure details (see .env.example for reference):

Code snippet
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-s3-bucket-name
SQS_QUEUE_URL=[https://sqs.us-east-1.amazonaws.com/123456789012/YourQueueName](https://sqs.us-east-1.amazonaws.com/123456789012/YourQueueName)
OPENSEARCH_ENDPOINT=your-endpoint-id.us-east-1.aoss.amazonaws.com

4. Running the Application
Because this is a decoupled architecture, you must run the web server and the background worker in two separate terminal windows.

Terminal 1: Start the Web UI

Bash
python app.py
Navigate to http://localhost:5000 in your browser.

Terminal 2: Start the Background Worker

Bash
python worker.py

## 📁 Project Structure
```text
enterprise-rag-agent/
│
├── app.py                 # Flask web server and webhook endpoints
├── worker.py              # Background processor listening to SQS
├── rag_engine.py          # LLM and OpenSearch query logic
├── requirements.txt       # Python dependencies
├── .env.example           # Example environment variables file
├── .gitignore             # Git ignore rules (protects secrets)
├── README.md              # Project documentation
│
└── templates/
    └── index.html         # Frontend user interface

