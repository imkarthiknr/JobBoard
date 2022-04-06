from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.config import setting

SQLALCHEMY_DATABASE_URL = setting.DATABASE_URL
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False,autoflush=False,bind=engine)