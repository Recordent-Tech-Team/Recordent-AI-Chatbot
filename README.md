# Recordent AI Chatbot

## Description
FastAPI backend service for Recordent chatbot workflows, including secured chat APIs, document embedding ingestion and rollback, retrieval-augmented response generation, admin analytics, and operational health endpoints.

## Features Included
- API key-based authentication for chat and admin routes
- Chat APIs for session creation, message processing, and session close
- Retrieval-augmented generation (RAG) with Bedrock chat + embedding models
- Embedding ingestion pipeline for document upload and vector updates
- Embedding versioning and rollback support
- Admin analytics and chat session/history endpoints
- Structured JSON response envelope middleware
- Centralized exception handling and error code mapping
- Request/response logging with separate app, error, and access logs
- CORS middleware support
- Health endpoint and startup dependency validations
- AWS integrations for Bedrock, S3, and session management
- Golden dataset and benchmark evaluation framework for LLM/RAG quality tracking

## Tech Stack
- Python 3.12
- FastAPI
- Uvicorn
- SQLAlchemy (async)
- PostgreSQL
- Loguru
- aioboto3 / AWS SDK
- Amazon Bedrock
- FAISS (vector index assets)
- DeepEval (preferred evaluator, with runtime fallback)

## Setup
Install dependencies:

```bash
pip install -r requirements.txt
```

Run in development (Windows helper script):

```bat
run_dev.bat
```

Run directly with Uvicorn:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --no-access-log
```

Run with Docker:

```bash
docker build -t recordent-ai-chatbot .
docker run -p 8000:8000 recordent-ai-chatbot
```

## APIs
- Health APIs: `/`, `/health-check`
- Chat APIs (v1): `/v1/chat/create-session`, `/v1/chat/send-message`, `/v1/chat/close-session`
- Admin APIs (v1): `/v1/admin/embeddings/update`, `/v1/admin/embeddings/versions`, `/v1/admin/embeddings/rollback`, `/v1/admin/chat/sessions`, `/v1/admin/chat/history?session_id=<uuid>`, `/v1/admin/analytics`
- Evaluation APIs (admin):
	- `/v1/admin/evaluation/golden-datasets`
	- `/v1/admin/evaluation/golden-datasets/{dataset_id}/cases:bulk`
	- `/v1/admin/evaluation/golden-datasets/{dataset_id}/cases`
	- `/v1/admin/evaluation/run-single`
	- `/v1/admin/evaluation/run-benchmark`
	- `/v1/admin/evaluation/runs/{run_id}`
	- `/v1/admin/evaluation/history`
	- `/v1/admin/evaluation/metrics`

## Performance Notes
- Chat evaluation is configurable using `CHAT_EVALUATION_ENABLED`.
- Default is `False` to reduce chat latency.
- Set `CHAT_EVALUATION_ENABLED=true` when you need evaluation scoring logs.

## Evaluation Framework
- Golden dataset template file is available at `app/prompts/golden_dataset_template.json`.
- Framework tracks retrieval metrics (recall, precision), answer metrics (correctness, relevancy, completeness), grounding metrics (faithfulness, hallucination), and citation support.
- Full benchmark runs are asynchronous and return a `run_id` for polling status.
- Dashboard metrics endpoint (`/v1/admin/evaluation/metrics`) returns:
	- Context Recall %
	- Context Precision %
	- Correctness %
	- Faithfulness %
	- Hallucination Rate %

## Test
No automated test command is currently documented in this repository.
If you have pytest configured in your environment, you can run:

```bash
pytest
```
