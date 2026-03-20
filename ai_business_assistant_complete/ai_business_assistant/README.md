# 🤖 AI Business Assistant

A production-ready FastAPI application that helps businesses with AI-powered marketing content generation, business planning, competitor analysis, and document-based Q&A using RAG (Retrieval-Augmented Generation).

---

## 🚀 Features

| Feature | Description |
|---|---|
| **Marketing Content** | Generate headlines, pitches, and CTAs for any business |
| **Business Plan Generator** | Write specific sections of a business plan |
| **Competitor Analysis** | Market analysis and differentiation strategies |
| **Social Media Posts** | Platform-specific posts (Instagram, LinkedIn, Twitter) |
| **RAG Q&A** | Upload documents and ask questions about them |
| **Semantic Search** | Find similar content chunks from your documents |

---

## 📁 Project Structure

```
ai_business_assistant/
├── main.py                    # FastAPI app entry point
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── data/
│   └── vectorstore/           # FAISS index stored here
└── app/
    ├── core/
    │   └── config.py          # Pydantic settings
    ├── routes/
    │   ├── ai_routes.py       # Marketing & content endpoints
    │   └── rag_routes.py      # RAG ingestion & query endpoints
    └── services/
        ├── ai_service.py      # LangChain LLM service
        └── rag_service.py     # FAISS + RAG service
```

---

## ⚙️ Setup

### 1. Clone and install

```bash
git clone <your-repo-url>
cd ai_business_assistant
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 3. Run the server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API Docs available at: **http://localhost:8000/docs**

---

## 🐳 Docker

```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d
```

---

## 📡 API Endpoints

### AI Content (`/api/ai`)

#### `POST /api/ai/generate-content`
Generate marketing content for a business.
```json
{
  "business_type": "online bakery",
  "goal": "increase online orders by 30%"
}
```

#### `POST /api/ai/business-plan`
Generate a business plan section.
```json
{
  "business_type": "SaaS startup",
  "section": "Executive Summary",
  "context": "B2B HR software for SMEs"
}
```

#### `POST /api/ai/competitor-analysis`
Analyze market competition.
```json
{
  "business_type": "fitness app",
  "market": "India tier-2 cities"
}
```

#### `POST /api/ai/social-media-posts`
Generate platform-specific posts.
```json
{
  "business_type": "handmade jewelry",
  "platform": "Instagram",
  "topic": "Diwali sale",
  "count": 3
}
```

---

### RAG Q&A (`/api/rag`)

#### `POST /api/rag/ingest`
Ingest documents into the vectorstore.
```json
{
  "texts": ["Your document content here..."],
  "sources": ["product_catalog.txt"],
  "store_name": "default"
}
```

#### `POST /api/rag/ingest-file`
Upload a `.txt` file directly.
```
Form data: file=<your_file.txt>, store_name=default
```

#### `POST /api/rag/query`
Ask a question using RAG.
```json
{
  "question": "What is the return policy?",
  "store_name": "default",
  "k": 4
}
```

#### `POST /api/rag/search`
Semantic similarity search (no LLM).
```json
{
  "query": "pricing information",
  "store_name": "default",
  "k": 5
}
```

#### `DELETE /api/rag/store/{store_name}`
Delete a vectorstore.

---

## ☁️ Cloud Deployment

### AWS (EC2)
```bash
# On EC2 instance
sudo apt update && sudo apt install docker.io docker-compose -y
git clone <repo>
cd ai_business_assistant
echo "OPENAI_API_KEY=sk-..." > .env
docker-compose up -d
```

### AWS (Elastic Beanstalk)
- Use `Dockerrun.aws.json` or the included `Dockerfile`
- Set env vars in EB console → Configuration → Environment properties

### Azure (App Service)
```bash
az webapp create --name ai-business-assistant --plan myPlan --runtime "PYTHON:3.11"
az webapp config appsettings set --name ai-business-assistant --settings OPENAI_API_KEY=sk-...
```

---

## 🔧 Git Workflow

```bash
git init
git add .
git commit -m "feat: initial AI business assistant"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main

# Feature branches
git checkout -b feature/add-email-generator
# ... make changes ...
git commit -m "feat: add email campaign generator"
git push origin feature/add-email-generator
# Create PR on GitHub
```

---

## 🧪 Testing

```bash
# Install test deps
pip install pytest httpx

# Run tests
pytest tests/ -v
```

---

## 📦 Tech Stack

- **FastAPI** — REST API framework
- **LangChain** — LLM orchestration & chains
- **OpenAI GPT-4o-mini** — Language model
- **FAISS** — Vector similarity search
- **Pydantic** — Data validation
- **Docker** — Containerization
- **Uvicorn** — ASGI server
