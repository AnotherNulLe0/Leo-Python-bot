import json
from threading import Thread, Event
from time import sleep
from locator import MyService
from models import get_all_users, add_location_record, get_tracked_users
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm.exc import DetachedInstanceError
import logging
from requests import ConnectionError
from urllib3.exceptions import NewConnectionError, MaxRetryError

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


class SessionCM:
    """Context manager for SQLAlchemy session."""

    def __init__(self, session):
        """Class constructor.

        Args:
            (Session): SQLAlchemy session.
        """
        self._session = session

    def __enter__(self):
        """Session initiator."""
        return self._session()

    def __exit__(self, type, value, traceback):
        """Session remover."""
        self._session.remove()


class Poller:
    def __init__(self, db_interface):
        self.users = None
        self.stopped = Event()
        self.thread = None
        self.db_interface = db_interface
        self.session = self._session

    @property
    def _session(self):
        Session = scoped_session(
            sessionmaker(
                autocommit=False, autoflush=False, bind=create_engine(self.db_interface, echo=False)
            )
        )
        return Session

    def poller(self):
        while not self.stopped.is_set():
            try:
                if self.users:
                    with SessionCM(self.session) as session:
                        for user in self.users:
                            service_objects = MyService(user.user_cookie, user.user_email)
                            for nickname in json.loads(user.tracked_objects):
                                person = service_objects.get_person_by_nickname(nickname)
                                logging.info(msg=f"polling {person.nickname}")
                                add_location_record(session, user.user_id, person)
                sleep(60)
            except DetachedInstanceError or ConnectionError or NewConnectionError or MaxRetryError as err:
                print(f"Thread exception: {err}")
                logging.info(msg=f"Thread exception: {err}")

        return "Thread stopped"

    def start(self):
        if not self.thread:
            with SessionCM(self.session) as session:
                self.users = get_all_users(self.session)
            self.stopped.clear()
            self.thread = Thread(target=self.poller)
            self.thread.start()
            print(f"thread started for: {self.users}")

    def stop(self):
        if self.thread:
            print("trying to stop")
            self.stopped.set()
            self.thread.join()
            self.stopped.clear()
            self.thread = None
            print("thread stopped")
            return
        print("Can't stop")

    def update(self):
        self.stop()
        with SessionCM(self.session) as session:
            self.users = get_all_users(self.session)
        self.start()
