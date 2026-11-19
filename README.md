# CMS Project (PVI)

This repository contains the CMS project composed of:
- **Frontend**: Vanilla JavaScript / HTML / CSS / PWA served with Nginx.
- **Backend**: FastAPI (Python 3.13) with SQLModel and Beanie.
- **PostgreSQL**: Relational database for students.
- **MongoDB**: Document database for messages and chats.

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
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

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
