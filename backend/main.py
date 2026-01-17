from fastapi import FastAPI
from mangum import Mangum
from routers import worlds

app = FastAPI()

# ルーターを登録
app.include_router(worlds.router)

@app.get("/")
def read_root():
    return {"message": "Hello FastAPI!"}

# for AWS Lambda function
handler = Mangum(app)
