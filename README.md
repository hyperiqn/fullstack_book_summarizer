# Intelligent Document Summarizer & RAG System

This project implements a comprehensive full-stack application that allows users to upload PDF documents, automatically generate summaries using Large Language Models (LLMs), and perform Retrieval-Augmented Generation (RAG) queries to chat with their documents. The system is designed for high performance and scalability, leveraging asynchronous processing and specialized LLM serving.

## Features

* **User Authentication:** Secure user registration and login.
* **Document Upload:** Upload PDF files to a secure S3 bucket.
* **Asynchronous Document Processing:**
    * PDF text extraction.
    * Text chunking for optimized retrieval.
    * Embedding generation.
    * Vector database storage (ChromaDB) for efficient similarity search.
    * **LLM-powered summarization** of uploaded documents.
    * All processing handled asynchronously via Celery workers for responsiveness.
* **Document Management:** View a list of uploaded documents and their processing status.
* **RAG-powered Chat:** Ask natural language questions about uploaded documents and receive contextually relevant answers from the LLM.
* **Performance Metrics:** Implemented load testing with Locust to benchmark system performance and identify bottlenecks.

## Video Demo

https://youtu.be/mgBqyUGxEjg

## Technologies Used

### Backend (FastAPI, Python)

* **FastAPI:** High-performance web framework.
* **SQLAlchemy (Async):** Asynchronous ORM for database interactions.
* **PostgreSQL:** Relational database for user and document metadata.
* **Celery:** Asynchronous task queue for background PDF processing.
* **Redis:** Message broker for Celery.
* **AWS S3:** Cloud storage for raw PDF files.
* **`httpx`:** Asynchronous HTTP client.
* **`passlib` & `bcrypt`:** For secure password hashing.
* **`langchain_text_splitters`:** For robust text chunking.

### AI/ML Components (External Host)

* **`vLLM`:** High-throughput and low-latency LLM serving engine, used for **horizontal scalability and efficient handling of concurrent requests**.
* **Large Language Models (LLMs):** Specifically **Mistral 7B 0.2 Quantized**, deployed via `vLLM` for summarization and RAG query answering. Hosted on a **college A100 GPU**, making efficient use of approximately **4GB of VRAM** during inference.
* **Embedding Models:** For converting text into numerical vectors sentence-transformers/all-MiniLM-L6-v2 was used.
* **ChromaDB:** Vector database for storing and retrieving document chunks.

### Frontend (React.js)

* **React:** JavaScript library for building user interfaces.
* **Create React App (CRA):** Popular tool for quickly setting up single-page React applications.
* **Tailwind CSS:** Utility-first CSS framework for rapid styling.
* **Axios:** Promise-based HTTP client for API requests.
* **`react-router-dom`:** For client-side routing.
* **`react-icons`:** For UI icons.
* **`react-spinners`:** For loading indicators.

### Load Testing

* **Locust:** Open-source load testing tool for simulating user behavior.

## Configuration Notes (For Developers/Maintainers)

This section outlines key configuration points for the application.
* **Install dependencies:** 
    ```env
    pip install -r requirements.txt
    ```

* **Backend Environment Variables (`.env`):**
    ```env
    DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/rag_db"
    SECRET_KEY="your_super_secret_key_here"
    ALGORITHM="HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES=30
    S3_ACCESS_KEY_ID="YOUR_AWS_ACCESS_KEY_ID"
    S3_SECRET_ACCESS_KEY="YOUR_AWS_SECRET_ACCESS_KEY"
    S3_REGION_NAME="your-aws-region"
    S3_BUCKET_NAME="your-s3-bucket-name"
    API_V1_STR="/api/v1"
    VLLM_API_BASE_URL="http://<EXTERNAL_HOST_IP_OR_HOSTNAME>:8000" # Example vLLM endpoint, adjust port if needed
    LLM_MODEL="mistralai/Mistral-7B-Instruct-v0.2" # Example HuggingFace model ID for vLLM
    EMBEDDING_MODEL_URL="http://<EMBEDDING_SERVICE_IP_OR_HOSTNAME>:<PORT>" # Example, if embedding is separate
    CELERY_BROKER_URL="redis://localhost:6379/0"
    CELERY_RESULT_BACKEND="redis://localhost:6379/0"
    DEBUG_MODE=True
    ```
    * **AWS Credentials:** Ensure `S3_ACCESS_KEY_ID` and `S3_SECRET_ACCESS_KEY` are configured for S3 access.
    * **LLM/Embedding Endpoint:** `VLLM_API_BASE_URL` should point to your `vLLM` server. If embeddings are served separately, configure `EMBEDDING_MODEL_URL`.
    * **Database/Redis:** Configure connection strings for PostgreSQL and Redis.

* **Frontend Environment Variables (`.env`):**
    ```env
    REACT_APP_API_BASE_URL=http://localhost:8001/api/v1
    ```
    * `REACT_APP_API_BASE_URL` should point to your FastAPI backend. CRA expects environment variables to be prefixed with `REACT_APP_`.

* **Local Infrastructure (Docker Compose):**
    The project typically relies on Docker Compose for local development services like PostgreSQL, Redis, and ChromaDB.

## Running the Application

This project is set up to be run locally in a development environment.
### 1. Start the Backend Services (PostgreSQL, Redis)

    docker start book_summarizer_postgres
###
    docker start book_summarizer_redis
###
    docker run --name book_summarizer_postgres -e POSTGRES_USER=user -e POSTGRES_PASSWORD=pass -e POSTGRES_DB=pg_db -p 5432:5432 -d postgres:latest
###
    docker run --name book_summarizer_redis -p 6379:6379 -d redis/redis-stack-server:latest
### 2. Running the vllm server(Run this on your gpu)
    python3 -m vllm.entrypoints.api_server --model TheBloke/Mistral-7B-Instruct-v0.2-AWQ --port 8888 --host 0.0.0.0
### 3. Running the app(fastapi, chromadb, celery, ssh tunnel)
    uvicorn main:app --host 0.0.0.0 --port 8001 --reload 
###
    celery -A app.tasks.celery_app worker --loglevel=info
###
    chroma run --path chroma_data --port 8000
###
    ssh -L 8002:localhost:8888 user@ip -p 6868 -N
## Performance Insights & Future Improvements

Load testing with Locust revealed that while the system maintains **0% failures** for **25 concurrent users**, the most resource-intensive operations still contribute significantly to overall latency. Specifically, the **document upload (which includes LLM summarization)** averages around **31 seconds**, and **RAG-powered queries** average **4.1 seconds** test. 

This performance profile is heavily influenced by the **Mistral-7B-Instruct-v0.2-AWQ** running on a college A100 GPU, consuming approximately 4GB of VRAM per instance. The `vLLM` framework efficiently manages this, but LLM inference remains the dominant factor in latency.

Potential avenues for further optimization include:

* **LLM Fine-tuning/Model Selection:** Exploring smaller, more aggressively quantized, or domain-specific LLMs if a balance between speed and quality can be achieved.
* **GPU Utilization Optimization:** Ensuring `vLLM` is fully leveraging the A100 GPU's capabilities, potentially through batching or advanced `vLLM` configurations.
* **Asynchronous Task Queue Scaling:** Increasing Celery worker concurrency and optimizing worker pool types.
* **Embedding Strategy:** Evaluating alternative embedding models or exploring parallel embedding generation techniques.
* **Network Latency:** Minimizing network latency between the backend and the external LLM/Embedding service host.
* **Horizontal Scaling:** Further distributing the FastAPI application and `vLLM` instances across multiple servers for higher throughput.

## Contributing

Feel free to fork this repository, contribute improvements, or suggest new features!

## License

This project is open-source and available under the [MIT License](LICENSE).
