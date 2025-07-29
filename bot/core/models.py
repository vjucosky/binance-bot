from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime
from sqlalchemy import func


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = 'BINANCE_BOT_EVENT'

    id: Mapped[int] = mapped_column('ID', primary_key=True)
    type: Mapped[str] = mapped_column('TYPE')
    timestamp: Mapped[int] = mapped_column('TIMESTAMP')
    created_at: Mapped[datetime] = mapped_column('CREATED_AT', server_default=func.current_date())
    payload: Mapped[str | None] = mapped_column('PAYLOAD')


class Response(Base):
    __tablename__ = 'BINANCE_BOT_RESPONSE'

    id: Mapped[int] = mapped_column('ID', primary_key=True)
    correlation_id: Mapped[str | None] = mapped_column('CORRELATION_ID')
    status: Mapped[int] = mapped_column('STATUS')
    created_at: Mapped[datetime] = mapped_column('CREATED_AT', server_default=func.current_date())
    payload: Mapped[str | None] = mapped_column('PAYLOAD')
