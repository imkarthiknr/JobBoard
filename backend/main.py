from fastapi import FastAPI
from core.config import setting
from db.session import engine
from db.base_class import Base

def create_tables():
    Base.metadata.create_all(bind=engine)

def start_application():
    app = FastAPI(title=setting.PROJECT_TITLE,version=setting.PROJECT_VERSION)
    create_tables()
    return app

app = start_application()
@app.get("/")
def hello_api():
    return{"detail":"Hello"}