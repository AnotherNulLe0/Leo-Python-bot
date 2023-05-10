from datetime import timedelta
import json
from threading import Thread, Event
from time import sleep
from datetime import datetime
from locator import MyService
from models import get_all_users, add_location_record, get_tracked_users, get_last_coordinates
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm.exc import DetachedInstanceError
import logging
from requests import ConnectionError
from urllib3.exceptions import NewConnectionError, MaxRetryError
from geopy.distance import distance

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
        if self.users:
            users_data = {}
            for user in self.users:
                with SessionCM(self.session) as session:
                    users_data[user.user_id]["last_location"] = get_last_coordinates(session, user.user_id)
                    users_data[user.user_id]["next_poll_time"] = datetime.now()
        else:
            return "No users found"
        
        while not self.stopped.is_set():
            queue = []
            try:
                with SessionCM(self.session) as session:
                    for user in self.users:
                        if users_data[user.user_id]["next_poll_time"] < datetime.now():
                            queue.append(user)
                            
                    for user in queue:
                        service_objects = MyService(user.user_cookie, user.user_email)
                        for nickname in json.loads(user.tracked_objects):
                            person = service_objects.get_person_by_nickname(nickname)
                            current_location = (person.latitude, person.longitude)
                            d = distance(current_location, users_data[user.user_id]["last_location"]).m
                            delta_seconds = 60 / ((d * 0.2) + 1)
                            next_poll_time = datetime.now() + timedelta(seconds=delta_seconds)
                            users_data[user.user_id]["last_location"] = current_location
                            users_data[user.user_id]["next_poll_time"] = next_poll_time
                            logging.info(msg=f"polled {person.nickname} distance : {d}m, delta seconds : {delta_seconds}")
                            if d != 0:
                                add_location_record(session, user.user_id, person)
                sleep(1)
            except Exception as err:
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
