# How to Run the Project

## 1. Backend

```bash
cd backend

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux / Mac:
source venv/bin/activate

# Install dependencies (first time only)
pip install -r requirements.txt

# Start server
python app.py
# → listening on http://localhost:5000
```

## 2. Frontend

**Option A — Python built-in server:**
```bash
cd frontend
python -m http.server 8000
# open http://localhost:8000 in browser
```

**Option B — VS Code Live Server extension:**
Right-click `frontend/index.html` → "Open with Live Server"

## Requirements

- Python 3.10+
- Webcam connected and accessible
- Modern browser (Chrome, Edge, Firefox)
- Both backend and frontend must be running simultaneously
