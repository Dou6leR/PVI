# CMS Project (PVI)

This repository contains the CMS project composed of:
- **Frontend**: Vanilla JavaScript / HTML / CSS / PWA served with Nginx.
- **Backend**: FastAPI (Python 3.13) with SQLModel, Beanie, and AI Agent (Google Gemini / RAG / MCP).
- **PostgreSQL**: Relational database for students.
- **MongoDB**: Document database for messages and chats.
- **AI & RAG Engine**: Gemini API with Tool Calling, PDF text ingestion (`pypdf`), vector similarity search, and Model Context Protocol (`/mcp`).

---

## Quick Start with Docker (Recommended)

### 1. Requirements
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

### 2. Configure Environment (Optional)
A default `.env` file is already provided. If needed, you can customize host ports and credentials in `.env`:
- `FRONTEND_HOST_PORT` (default: `3000`)
- `BACKEND_HOST_PORT` (default: `8000`)
- `POSTGRES_HOST_PORT` (default: `5433` to prevent collision with local PostgreSQL on `5432`)
- `MONGO_HOST_PORT` (default: `27018`)

### 3. Build & Run
Run the entire application stack:
```bash
docker compose up --build -d
```

### 4. Access the Application
- **Frontend**: [http://localhost:3000](http://localhost:3000) (Login page)
- **Backend API Docs (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **pgAdmin (Web UI для PostgreSQL)**: [http://localhost:5050](http://localhost:5050)
- **n8n Workflow Automation**: [http://localhost:5678](http://localhost:5678)
- **Tasks & AI Quiz Generator**: [http://localhost:3000/tasks_page/tasks.html](http://localhost:3000/tasks_page/tasks.html)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **AI Status Endpoint**: [http://localhost:8000/api/v1/ai/status](http://localhost:8000/api/v1/ai/status)
- **MCP Server (Model Context Protocol)**: `http://localhost:8000/mcp`

---

## AI Developer Capabilities (Monobank Internship Showcase)

This application includes a complete, enterprise-grade AI architecture:

### 1. API моделей у коді (Google Gemini)
- Integrated via official `google-genai` SDK (`gemini-2.5-flash`).
- Smart Offline Fallback Engine: seamlessly operates with full functionality even before an API key is supplied!

### 2. AI-агент з Tool Calling (Function Calling)
- The **CMS AI Assistant** autonomously selects and calls backend tools:
  - `search_students(query)`: searches student records in PostgreSQL.
  - `get_group_students(group)`: retrieves group members in PostgreSQL.
  - `get_system_stats()`: computes live statistics and group distribution.
  - `query_subject_knowledge(query, subject)`: queries the RAG vector store.
  - `add_knowledge(subject, title, content)`: dynamically adds knowledge notes from chat.

### 3. Предметні чати (Subject Scoping)
- Create separate chats for different courses (e.g., *ПВІ*, *Бази даних*, *Комп'ютерні мережі*).
- Each chat maintains its own subject context, isolating knowledge bases and conversation flow.

### 4. Завантаження PDF у чаті (PDF Ingestion & RAG)
- Click **📎 PDF** directly in the chat to upload any course syllabus, lecture slides, or lab guidelines.
- The backend parses the PDF via `pypdf`, chunks the text, creates vector embeddings, and stores them in the RAG store.
- The AI answers questions using extracted document chunks and cites exact file names and page numbers.

### 5. MCP-сервер (Model Context Protocol)
- Standard endpoint at `http://localhost:8000/mcp`.
- Follows the JSON-RPC 2.0 MCP specification created by Anthropic, enabling external AI clients (Claude Desktop, Cursor, Antigravity) to access CMS database tools.

### 6. n8n Workflow Automation & Tasks Quiz Generator
- Self-hosted n8n instance running in Docker on [http://localhost:5678](http://localhost:5678).
- Visual automation workflow template in `n8n/workflows/quiz_generator.json`.
- **100% Privacy-Preserving (Zero PII)**: Webhooks process only academic subject & topic strings (`{"subject": "ПВІ", "topic": "Docker"}`). Zero student personal data is ever exposed.
- Interactive self-testing UI on the **Tasks** page ([http://localhost:3000/tasks_page/tasks.html](http://localhost:3000/tasks_page/tasks.html)) with scoring, options coloring, and AI explanations.


### 5. Populate Initial Data
To populate the PostgreSQL database with mock students:
```bash
docker compose exec backend python app/actions/populate_student.py
```

### 6. Stop Containers
To stop the services:
```bash
docker compose down
```
To stop and remove data volumes:
```bash
docker compose down -v
```

---

## Local Development (Without Docker)

### Backend Setup (FastAPI)
1. Navigate to the backend directory:
   ```bash
   cd back-end
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```

3. Run FastAPI development server:
   ```bash
   poetry run uvicorn main:app --app-dir app --host 0.0.0.0 --port 8000 --reload
   ```

### Frontend Setup
Open `front-end/index.html` with VS Code Live Server (`http://127.0.0.1:5500`).
