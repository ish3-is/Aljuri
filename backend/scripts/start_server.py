
import sys
import os
import asyncio
import uvicorn

# Clean environment - no PYTHONPATH from the Hermes venv
env = {
    "PATH": r"C:\Program Files\Python312;" + os.environ.get("PATH", ""),
    "PYTHONNOUSERSITE": "1",
    "PYTHONUNBUFFERED": "1",
}

# Prepend the project venv site-packages to sys.path
sys.path.insert(0, r"D:/MDR/Aljuri-Greadute-Project/backend/.venv/Lib/site-packages")
sys.path.insert(0, r"D:/MDR/Aljuri-Greadute-Project/backend")

print("Starting backend...", flush=True)

async def main():
    from app.main import app
    print("App imported OK", flush=True)
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

try:
    asyncio.run(main())
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Error: {e}", flush=True)
