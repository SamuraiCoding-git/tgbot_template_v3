from typing import List
from sqlalchemy import String, Integer, text, BIGINT
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, TableNameMixin

from sqlalchemy.orm import relationship
from infrastructure.database.models.user_tasks import UserTask  # Ensure this import is correct

class User(Base, TimestampMixin, TableNameMixin):
    user_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=False)
    balance: Mapped[int] = mapped_column(Integer, default=1000)
    language: Mapped[str] = mapped_column(String(10), server_default=text("'en'"))

    # Define the relationship with UserTask
    tasks: Mapped[List["UserTask"]] = relationship("UserTask", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.user_id} {self.balance} {self.language}>"

