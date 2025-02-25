import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse 
from backend.api import ec2, s3, route53

app = FastAPI()

# Defineng allowed origins 
origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://0.0.0.0:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# absolute path to the frontend folder.
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")

# mounting static assets at "/frontend"
app.mount("/frontend", StaticFiles(directory=frontend_path), name="frontend")

# Createing a route for "/" to serve index.html
@app.get("/")
async def read_index():
    return FileResponse(os.path.join(frontend_path, "index.html"))



app.include_router(ec2.router, prefix="/api/ec2")
app.include_router(s3.router, prefix="/api/s3")
app.include_router(route53.router, prefix="/api/route53")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
