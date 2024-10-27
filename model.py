from sqlalchemy import Column, Integer, Text, DateTime, create_engine, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database setup (using SQLite)
DATABASE_URL = "sqlite:///./socket.db"

# SQLAlchemy engine and session
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# ChatEntry model with prompt, response, and timestamp
class ChatEntry(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    client = Column(Text, nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now(), index=True)  # UTC timestamp with index

# Create the table in the database
Base.metadata.create_all(bind=engine)
