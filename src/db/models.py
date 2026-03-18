from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import relationship

from db.database import Base


class UserRecord(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    files = relationship(
        "FileRecord", back_populates="user", cascade="all, delete-orphan"
    )


class FileRecord(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    original_name = Column(String, nullable=False)
    stored_name = Column(String, nullable=False)
    path = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    size = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("UserRecord", back_populates="files")
    content = relationship(
        "FileContentRecord",
        back_populates="file",
        uselist=False,
        cascade="all, delete-orphan",
    )
    chunks = relationship(
        "ChunkRecord", back_populates="file", cascade="all, delete-orphan"
    )


class FileContentRecord(Base):
    __tablename__ = "file_content"

    file_id = Column(Integer, ForeignKey("files.id"), primary_key=True)
    # GIN index for efficient full-text search — avoids btree row-size limits on large tsvectors
    content_tsv = Column(TSVECTOR, nullable=False)

    __table_args__ = (
        Index(
            "ix_file_content_content_tsv",
            "content_tsv",
            postgresql_using="gin",
        ),
    )

    file = relationship("FileRecord", back_populates="content")


class ChunkRecord(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    text = Column(String, nullable=False)
    embedding = Column(Vector(1024), nullable=False)
    model = Column(String, nullable=False, default="voyage-3")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    file = relationship("FileRecord", back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("file_id", "chunk_index", name="uq_chunks_file_chunk"),
        # ivfflat index NN cosine search
        Index(
            "ix_chunks_embedding_vec",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
