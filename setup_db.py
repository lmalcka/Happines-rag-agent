import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

# 1. Add your OpenSearch Serverless Endpoint (NO https://)
OPENSEARCH_ENDPOINT = "3jybqelpsv9fwcblfl7d.us-east-1.aoss.amazonaws.com"
REGION = "us-east-1"

# 2. Authenticate
credentials = boto3.Session().get_credentials()
auth = AWSV4SignerAuth(credentials, REGION, 'aoss')

client = OpenSearch(
    hosts=[{'host': OPENSEARCH_ENDPOINT, 'port': 443}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
)

# 3. The Blueprint (Schema)
index_body = {
  "settings": {
    "index.knn": True
  },
  "mappings": {
    "properties": {
      "embedding": {
        "type": "knn_vector",
        "dimension": 1536
      },
      "text": {
        "type": "text"
      }
    }
  }
}

# 4. Send the command to create the index
try:
    response = client.indices.create(index="happiness-index", body=index_body)
    print("✅ Success! The vector database blueprint has been created.")
    print(response)
except Exception as e:
    print("❌ Error creating index:", e)