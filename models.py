import json
import logging
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass
from sqlalchemy import (
    ForeignKey,
    String,
    Float,
    Boolean,
    Integer,
    DateTime,
    select,
    insert,
    update,
    and_,
    inspect,
    delete,
)
from sqlalchemy.orm import (
    Session,
    DeclarativeBase,
    Mapped,
    mapped_column,
    Bundle,
)

logger_app = logging.getLogger(__name__)

DEFAULT_USER_STATE = "initial"


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
            message = f"{self.instance.text}, {self.context.args}"
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


class Users(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer(), unique=True)
    user_state: Mapped[str] = mapped_column(String(), default="initial")
    user_cookie: Mapped[str] = mapped_column(String(), default="")
    tracked_objects: Mapped[str] = mapped_column(String(), default="[]")
    user_email: Mapped[str] = mapped_column(String(), default="")

    def __repr__(self):
        return f"{self.user_email}, {self.user_state}"


class Location(Base):
    __tablename__ = "locator"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner: Mapped[int] = mapped_column(ForeignKey("user.user_id"))
    full_name: Mapped[str] = mapped_column(String(), default="")
    nickname: Mapped[str] = mapped_column(String(), default="")
    current_location: Mapped[str] = mapped_column(String(), default="")
    latitude: Mapped[float] = mapped_column(Float())
    longitude: Mapped[float] = mapped_column(Float())
    timestamp: Mapped[datetime] = mapped_column(DateTime())
    charging: Mapped[int] = mapped_column(Boolean(), default=False)
    battery: Mapped[int] = mapped_column(Integer(), default="")
    accuracy: Mapped[int] = mapped_column(Integer(), default="")


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
    data = {
        "user_id": record.user_id,
        "username": record.username,
        "chat_id": record.chat_id,
        "type": record.type,
        "message": record.message,
        "message_id": record.message_id,
        "timestamp": record.timestamp,
    }
    chat_log_record = ChatLog(**data)
    session.add(chat_log_record)
    session.commit()
    return chat_log_record.id


def add_user(session: Session, user_id: int) -> str:
    data = {
        "user_id": user_id,
        "user_state": DEFAULT_USER_STATE,
    }
    user = Users(**data)
    session.add(user)
    session.commit()
    return user


def delete_user(session: Session, user_id: int, obj: str) -> bool:
    existing = session.scalar(select(Users.tracked_objects).where(Users.user_id == user_id))
    if existing:
        existing = json.loads(existing)
        existing.remove(obj)
        existing = json.dumps(existing)
        new_objects = update(Users).where(Users.user_id == user_id).values(tracked_objects=existing)
        locations = delete(Location).where(and_(Location.owner == user_id, Location.nickname == obj))
        session.execute(locations)
        session.execute(new_objects)
        return
    return "User does not exist"
    
    
def get_user(session: Session, user_id: int) -> Users:
    return session.scalar(select(Users).where(Users.user_id == user_id))


def set_user_state(session: Session, user_id: int, state: str) -> bool:
    new_state = update(Users).where(Users.user_id == user_id).values(user_state=state)
    res = session.execute(new_state)
    session.commit()

    return True if res.rowcount == 1 else False


def add_user_email(session: Session, user_id: int, email: str) -> bool:
    new_email = update(Users).where(Users.user_id == user_id).values(user_email=email)
    res = session.execute(new_email)
    session.commit()

    return True if res.rowcount == 1 else False


def add_user_cookie(session: Session, user_id: int, cookie: str) -> bool:
    new_cookie = update(Users).where(Users.user_id == user_id).values(user_cookie=cookie)
    res = session.execute(new_cookie)
    session.commit()

    return True if res.rowcount == 1 else False


def add_tracking_object(session: Session, user_id: int, obj: str) -> bool:
    existing = session.scalar(select(Users.tracked_objects).where(Users.user_id == user_id))
    if existing:
        existing = json.loads(existing)
        existing.extend([obj])
        existing = json.dumps(existing)
        new_objects = update(Users).where(Users.user_id == user_id).values(tracked_objects=existing)
        res = session.execute(new_objects)
        session.commit()

        return True if res.rowcount == 1 else False


def add_location_record(session: Session, owner, person) -> bool:
    data = {
        "owner": owner,
        "full_name": person.full_name,
        "nickname": person.nickname,
        "current_location": person.address,
        "latitude": person.latitude,
        "longitude": person.longitude,
        "timestamp": datetime.fromtimestamp(int(person.timestamp)/1000),
        "charging": person.charging,
        "battery": person.battery_level,
        "accuracy": person.accuracy,
    }
    location_record = Location(**data)
    session.add(location_record)
    session.commit()
    return location_record.id


def get_all_users(session: Session) -> List:
    return list(session.scalars(select(Users).where(Users.tracked_objects != "[]")))


def get_coordinates(session: Session, owner_id, nickname, timeframe):
    columns = Bundle("columns", Location.latitude, Location.longitude)
    res = session.scalars(select(columns).where(
        and_(Location.owner == owner_id, Location.nickname == nickname,
             Location.timestamp.between(timeframe[0], timeframe[1])))).unique()
    return res


def get_last_coordinates(session: Session, owner_id, nickname):
    columns = Bundle("columns", Location.latitude, Location.longitude)
    res = session.scalars(select(columns).where(
        and_(Location.owner == owner_id, Location.nickname == nickname)).order_by(Location.id.desc())).first()
    return res


def get_tracked_users(session: Session, owner_id):
    tracked = session.scalar(select(Users.tracked_objects).where(Users.user_id == owner_id))
    return json.loads(tracked)
