import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

FRONTEND_URL = os.environ.get("FRONTEND_URL")
if not FRONTEND_URL:
    raise RuntimeError("FRONTEND_URL must be set")

app = FastAPI()

# CORS
origins = [FRONTEND_URL]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello FastAPI!"}

# for AWS Lambda function
handler = Mangum(app)
