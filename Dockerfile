FROM python:3.10-slim

WORKDIR /app

# Install system dependencies required for FAISS and compilation
RUN apt-get update && apt-get install -y build-essential libopenblas-dev

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]