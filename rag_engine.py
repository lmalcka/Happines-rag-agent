import os
import json
import boto3
import kagglehub
import pandas as pd
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from dotenv import load_dotenv

load_dotenv()

class RAGEngine:
    def __init__(self):
        # 1. AWS Bedrock Client for Embeddings and LLM Inference
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=os.getenv('AWS_REGION', 'us-east-1'))

        # 2. Amazon OpenSearch Serverless Setup
        # REPLACE THIS WITH YOUR ACTUAL AOSS ENDPOINT (Do not include https://)
        self.opensearch_endpoint = os.getenv("OPENSEARCH_ENDPOINT")
        self.index_name = "happiness-index"

        print("[*] Connecting to Amazon OpenSearch Serverless...")
        credentials = boto3.Session().get_credentials()
        auth = AWSV4SignerAuth(credentials, os.getenv('AWS_REGION', 'us-east-1'), 'aoss')

        self.os_client = OpenSearch(
            hosts=[{'host': self.opensearch_endpoint, 'port': 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection
        )
        print("[✓] OpenSearch Connection Initialized.")

    def download_and_ingest_kaggle(self):
        """Downloads the Kaggle dataset and seeds the OpenSearch Database."""
        print("[*] Fetching Kaggle Dataset...")
        path = kagglehub.dataset_download("elvisbui/world-happiness-report-2005-2025-panel")
        print("\n[✓] Extraction complete!")

        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith('.csv'):
                    self._process_csv(os.path.join(root, file))

    def _process_csv(self, file_path):
        print(f"[*] Opening CSV file: {file_path}")
        df = pd.read_csv(file_path)

        # 🧪 TEST LIMIT: Processing only 10 rows for quick initialization
        print("[!] TEST MODE: Slicing dataset to the first 10 rows.")
        df = df.head(10)

        for index, row in df.iterrows():
            chunk = " | ".join([f"{col}: {val}" for col, val in row.items()])
            self.add_document(chunk)

            if (index + 1) % 2 == 0:
                print(f"    -> Progress: {index + 1}/10 embedded to OpenSearch...")

        print("[✓] Kaggle DB Seeding complete.")

    def add_document(self, text):
        """Generates an embedding via Titan and pushes it directly to OpenSearch."""
        embedding = self._get_embedding(text)
        if embedding:
            document = {
                "text": text,
                "embedding": embedding
            }
            try:
                # Push the document to the OpenSearch index
                self.os_client.index(index=self.index_name, body=document)
            except Exception as e:
                print(f"[!] OpenSearch Save Error: {e}")

    def _get_embedding(self, text):
        """Calls AWS Titan to create a 1536-dimensional vector."""
        try:
            body = json.dumps({"inputText": text})
            response = self.bedrock_client.invoke_model(
                body=body,
                modelId='amazon.titan-embed-text-v1',
                accept='application/json',
                contentType='application/json'
            )
            return json.loads(response.get('body').read()).get('embedding')
        except Exception as e:
            print(f"[!] Embedding Error: {e}")
            return None

    def ask_question(self, query):
        """Vectorizes the user query, searches OpenSearch, and asks Claude."""
        query_embedding = self._get_embedding(query)
        if not query_embedding:
            return "Failed to generate query embedding."

        # Search OpenSearch using K-Nearest Neighbors (KNN)
        os_query = {
            "size": 3,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_embedding,
                        "k": 3
                    }
                }
            }
        }

        try:
            # Execute the search against your AWS cluster
            os_response = self.os_client.search(index=self.index_name, body=os_query)

            # Extract the text chunks from the OpenSearch response hits
            hits = os_response['hits']['hits']
            if not hits:
                return "I couldn't find any relevant data in the vault."

            context = "\n".join([hit['_source']['text'] for hit in hits])

        except Exception as e:
            return f"Database Error: Is the OpenSearch collection running and index created? Details: {str(e)}"

        # 🚀 Pass the retrieved context to Claude 4.5 Haiku via Converse API
        model_id = "arn:aws:bedrock:us-east-1:113121189906:inference-profile/global.anthropic.claude-haiku-4-5-20251001-v1:0"
        prompt = f"Context:\n{context}\n\nQuestion: {query}\nAnswer strictly based on the context provided."

        try:
            response = self.bedrock_client.converse(
                modelId=model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": 32000, "temperature": 0.5, "stopSequences": []}
            )
            return response['output']['message']['content'][0]['text']

        except Exception as e:
            return f"Error querying Claude: {str(e)}"