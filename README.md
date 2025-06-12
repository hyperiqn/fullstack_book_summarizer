# Fullstack Document Summarizer & RAG Application

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

[![Watch the video here!](https://placehold.co/600x400/CCCCCC/333333?text=Click+to+Watch+Video)](YOUR_VIDEO_LINK_HERE)
*(Click the image to watch a 4-minute video demonstrating the application's functionality and a brief overview of its features.)*

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
* **Large Language Models (LLMs):** Specifically **Mistral-7B-Instruct-v0.2-AWQ**, deployed via `vLLM` for summarization and RAG query answering. Hosted on a **college A100 GPU**, making efficient use of approximately **4GB of VRAM** during inference.
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
