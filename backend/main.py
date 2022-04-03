from fastapi import FastAPI
from core.config import setting

app = FastAPI(title=setting.PROJECT_TITLE,version=setting.PROJECT_VERSION)

@app.get("/")
def hello_api():
    return{"detail":"Hello"}