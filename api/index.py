import sys
import os

# Ensure backend directory is in sys.path so app imports resolve properly on Vercel
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


try:
    from app.main import app
except ImportError:
    from backend.app.main import app  # type: ignore

# Vercel serverless entrypoint
handler = app

