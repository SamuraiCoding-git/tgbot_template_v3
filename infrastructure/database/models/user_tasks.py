from sqlalchemy import ForeignKey, Boolean, BIGINT
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base import Base, TimestampMixin, TableNameMixin

class UserTask(Base, TimestampMixin, TableNameMixin):
    __tablename__ = "user_tasks"

    user_id: Mapped[int] = mapped_column(BIGINT, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    task_id: Mapped[int] = mapped_column(BIGINT, ForeignKey("tasks.task_id", ondelete="CASCADE"), primary_key=True)
    status: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="tasks")
    task = relationship("Task", back_populates="user_tasks")

    def __repr__(self):
        return f"<UserTask(user_id={self.user_id}, task_id={self.task_id}, status={self.status})>"
