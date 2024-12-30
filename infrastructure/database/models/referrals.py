from sqlalchemy import Integer, BIGINT
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, TableNameMixin


class Referral(Base, TimestampMixin, TableNameMixin):
    """
    This class represents a User in the application.
    If you want to learn more about SQLAlchemy and Alembic, you can check out the following link to my course:
    https://www.udemy.com/course/sqlalchemy-alembic-bootcamp/?referralCode=E9099C5B5109EB747126

    Attributes:
        user_id (Mapped[int]): The unique identifier of the user.
        language (Mapped[str]): The language preference of the user.

    Methods:
        __repr__(): Returns a string representation of the User object.

    Inherited Attributes:
        Inherits from Base, TimestampMixin, and TableNameMixin classes, which provide additional attributes and functionality.

    Inherited Methods:
        Inherits methods from Base, TimestampMixin, and TableNameMixin classes, which provide additional functionality.

    """
    referral_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=False)
    referred_by: Mapped[int] = mapped_column(BIGINT, nullable=True)
    reward_type: Mapped[int] = mapped_column(Integer, default=1)

    def __repr__(self):
        return f"<User {self.referral_id} {self.referred_by} {self.reward_type}>"
