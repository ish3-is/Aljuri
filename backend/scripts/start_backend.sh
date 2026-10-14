import sys
sys.path.insert(0, r'D:/MDR/Aljuri-Greadute-Project\backend\.venv\Lib\site-packages')
# Insert backend dir
sys.path.insert(0, r'D:/MDR/Aljuri-Greadute-Project\backend')
import uvicorn
import asyncio

print("Starting backend...")

async def main():
    from app.main import app
    print("App imported OK")
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

asyncio.run(main())
