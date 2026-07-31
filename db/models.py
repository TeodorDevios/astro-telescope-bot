from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .core import Base

class User(Base):
    __tablename__ = "users"
    
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)
    tz_offset: Mapped[int] = mapped_column(default=3)
    telescope: Mapped["Telescope"] = relationship(back_populates="user", uselist=False)

class Telescope(Base):
    __tablename__ = "telescopes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"))
    diameter: Mapped[float] = mapped_column()
    focal_length: Mapped[float] = mapped_column()
    user: Mapped["User"] = relationship(back_populates="telescope")
    eyepieces: Mapped[list["Eyepiece"]] = relationship(back_populates="telescope")

class Eyepiece(Base):
    __tablename__ = "eyepieces"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telescope_id: Mapped[int] = mapped_column(ForeignKey("telescopes.id", ondelete="CASCADE"))
    eyepiece_focal_length: Mapped[float] = mapped_column()
    name: Mapped[str] = mapped_column()
    is_active: Mapped[bool] = mapped_column(default=False)
    telescope: Mapped["Telescope"] = relationship(back_populates="eyepieces")
