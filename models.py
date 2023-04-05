import logging
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass
from sqlalchemy import (
    ForeignKey,
    String,
    Integer,
    DateTime,
    select,
    insert,
    update,
    and_,
    inspect,
)
from sqlalchemy.orm import (
    Session,
    DeclarativeBase,
    Mapped,
    mapped_column,
    Bundle,
)

logger_app = logging.getLogger(__name__)


@dataclass
class ChatLogRecord:
    """Dataclass represent a database record for a message."""

    user_id: int
    username: str
    chat_id: int
    type: int
    message_id: int
    timestamp: datetime
    message: Optional[str] = None
    id: Optional[int] = None


class DataclassFactory:
    """Create an instance of the ChatLogRecord in depends of type of Update and Context."""
    
    def __init__(self, update, context):
        self.instance = update.effective_message
        self.context = context

    def run(self):
        if self.context.args is not None:
            print("\n\n", self.context.args, "\n\n")
            message = f"/{self.instance.text}, {self.context.args}"
        else:
            message = self.instance.text

        return ChatLogRecord(
            user_id=self.instance.from_user.id,
            username=self.instance.from_user.username,
            chat_id=self.instance.chat.id,
            type=self.instance.chat.type.name,
            message=message,
            message_id=self.instance.id,
            timestamp=self.instance.date,
        )
        # Message(channel_chat_created=False, chat=Chat(first_name='Kirill', id=227224447, type=<ChatType.PRIVATE>, username='the_one_kirill'), date=datetime.datetime(2023, 4, 5, 15, 7, 1, tzinfo=datetime.timezone.utc), delete_chat_photo=False, edit_date=datetime.datetime(2023, 4, 5, 15, 9, 36, tzinfo=datetime.timezone.utc), from_user=User(first_name='Kirill', id=227224447, is_bot=False, language_code='en', username='the_one_kirill'), group_chat_created=False, message_id=291, supergroup_chat_created=False, text='test2')


class Base(DeclarativeBase):
    """Declarative base class"""

    pass


class ChatLog(Base):
    __tablename__ = "chat_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer())
    username: Mapped[str] = mapped_column(String())
    chat_id: Mapped[int] = mapped_column(Integer())
    type: Mapped[str] = mapped_column(String())  # chat type
    message: Mapped[str] = mapped_column(String())
    message_id: Mapped[int] = mapped_column(Integer())
    timestamp: Mapped[datetime] = mapped_column(DateTime())

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


def insert_chat_log(session: Session, record: ChatLogRecord) -> int:
    insert = {
        "user_id": record.user_id,
        "username": record.username,
        "chat_id": record.chat_id,
        "type": record.type,
        "message": record.message,
        "message_id": record.message_id,
        "timestamp": record.timestamp,
    }
    chat_log_record = ChatLog(**insert)
    session.add(chat_log_record)
    session.commit()
    print(f"Record: {chat_log_record}")
    return chat_log_record.id
