import logging
from sqlalchemy import ForeignKey, String, Integer, select, insert, update, and_, inspect
from sqlalchemy.orm import (
    Session,
    DeclarativeBase,
    Mapped,
    mapped_column,
    Bundle,
)

logger_app = logging.getLogger(__name__)

class Base(DeclarativeBase):
    """Declarative base class"""

    pass


class ChatLog(Base):
    
    __tablename__ = "chat_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer())
    username: Mapped[str] = mapped_column(String())
    chat_id: Mapped[int] = mapped_column(Integer())
    type: Mapped[str] = mapped_column(String()) # chat type
    message: Mapped[str] = mapped_column(String())

    def __repr__(self) -> str:
        return f"{self.username}({self.user_id}), {self.message}(self.type)"
    
def init_db(session):
    """Database initialization.

    Args:
        session (Session): SQLAlchemy session.
    """
    if inspect(session.bind.engine).get_table_names() == []:
        Base.metadata.create_all(session.bind.engine)
    logger_app.debug(msg="Deleting all data from DB")
    session.commit()
