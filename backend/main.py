from fastapi import FastAPI
from mangum import Mangum

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello FastAPI!"}

# for AWS Lambda function
handler = Mangum(app)
