import sys
import os

# Ensure backend directory is in sys.path so app imports resolve properly on Vercel
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app, ensure_active_data
from app.storage.database import init_db, seed_october_baseline_if_missing

# Eagerly initialize DB and active master data on serverless cold-start
try:
    init_db()
    seed_october_baseline_if_missing()
    ensure_active_data()
except Exception as e:
    print(f"[Vercel Init] Notice: {e}")

# Vercel serverless entrypoint
handler = app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
