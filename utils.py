from threading import Thread, Event
from time import sleep
from locator import MyService
from models import get_all_users, add_location_record


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
    def __init__(self, session):
        self.session = session
        self.users = None
        self.stopped = Event()
        self.thread = None

    def poller(self):
        while not self.stopped.is_set():
            if self.users:
                for user in self.users:
                    service_objects = MyService(user.user_cookie, user.user_email)
                    for person in service_objects.get_all_people():
                        add_location_record(self.session, user.user_id, person)
                        print(f"polling {person.nickname}")
            sleep(60)
        print("Thread stopped")
        return "Thread stopped"

    def start(self):
        if not self.thread:
            self.users = get_all_users(self.session)
            self.stopped.clear()
            self.thread = Thread(target=self.poller)
            self.thread.start()
            print("thread started")

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
        self.users = get_all_users(self.session)
        self.start()

