import datetime as dt

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship

from opengaterag.api.schemas.collections import CollectionVisibility

Base = declarative_base()

UtcDateTime = DateTime(timezone=True)


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    create_public_collection: Mapped[bool] = mapped_column(default=False)
    storage_limit: Mapped[int | None] = mapped_column(default=None)
    created: Mapped[dt.datetime] = mapped_column(UtcDateTime, insert_default=func.now())
    updated: Mapped[dt.datetime] = mapped_column(UtcDateTime, insert_default=func.now(), onupdate=func.now())

    collection: Mapped[list["Collection"]] = relationship(back_populates="user", passive_deletes=True)


class Collection(Base):
    __tablename__ = "collection"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(column="user.id", ondelete="CASCADE"))
    name: Mapped[str]
    description: Mapped[str | None]
    visibility: Mapped[CollectionVisibility]
    created: Mapped[dt.datetime] = mapped_column(UtcDateTime, insert_default=func.now())
    updated: Mapped[dt.datetime] = mapped_column(UtcDateTime, insert_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="collection")
    document: Mapped[list["Document"]] = relationship(back_populates="collection", cascade="all, delete-orphan", passive_deletes=True)


class Document(Base):
    __tablename__ = "document"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey(column="collection.id", ondelete="CASCADE"))
    name: Mapped[str]
    size: Mapped[int] = mapped_column(default=0)
    created: Mapped[dt.datetime] = mapped_column(UtcDateTime, insert_default=func.now())

    collection: Mapped["Collection"] = relationship(back_populates="document", passive_deletes=True)
