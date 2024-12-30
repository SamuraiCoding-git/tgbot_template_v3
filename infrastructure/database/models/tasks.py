from typing import Optional, List

from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import String, BIGINT, JSON, Integer

from .base import Base, TimestampMixin, TableNameMixin
from infrastructure.database.models.user_tasks import UserTask

class Task(Base, TimestampMixin, TableNameMixin):
    __tablename__ = "tasks"

    task_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    titles: Mapped[dict] = mapped_column(JSON, nullable=False)  # {"en": "Title in English", "ru": "Title in Russian"}
    descriptions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # {"en": "Description in English", "ru": "Description in Russian"}
    source: Mapped[str] = mapped_column(String)
    link: Mapped[str] = mapped_column(String)
    cover: Mapped[Optional[str]] = mapped_column(String)
    balance: Mapped[int] = mapped_column(Integer)

    # Establish relationship with UserTask
    user_tasks: Mapped[List["UserTask"]] = relationship("UserTask", back_populates="task", cascade="all, delete-orphan")

    def __repr__(self):
        return (f"<Task(task_id={self.task_id}, titles={self.titles}, source={self.source}, "
                f"link={self.link}, cover={self.cover})>")
