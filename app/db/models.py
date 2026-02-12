from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()

class DuplicateGroup(Base):
    __tablename__ = 'duplicate_groups'
    
    id = Column(Integer, primary_key=True, index=True)
    hash_value = Column(String, unique=True, index=True)
    file_size = Column(Integer)
    
    files = relationship("FileEntry", back_populates="group", cascade="all, delete-orphan")

class FileEntry(Base):
    __tablename__ = 'file_entries'
    
    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, unique=True, index=True)
    filename = Column(String)
    is_original = Column(Boolean, default=False)
    group_id = Column(Integer, ForeignKey('duplicate_groups.id'))
    
    group = relationship("DuplicateGroup", back_populates="files")

# Database Setup
DATABASE_URL = "sqlite:///./files.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
