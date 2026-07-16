Backend Setup (FastAPI)

The backend is built with FastAPI, using `uv` to manage the virtual environment and packages.

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Install the backend dependencies:
```bash
poetry install
```

3. Run the FastAPI development server:
```bash
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The API will be live at: http://localhost:8000

Mongo Setup:
```bash
docker-compose up -d
```
