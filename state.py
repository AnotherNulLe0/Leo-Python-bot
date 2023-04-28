from models import add_user_cookie, add_tracking_object, add_user_email, set_user_state
from locator import MyService
from models import Users


class UserState:
    def __init__(self, user, session):
        self.user: Users = user
        self.session = session
        self.state = user.user_state
        self.transitions = {
            "initial": {
                "msg": "configurator started",
                "locator": "waiting_email",
                "reset": "initial",
                "error": "errored",
            },
            "waiting_email": {
                "msg": "input your email",
                "got_email": "waiting_cookies",
                "reset": "initial",
                "error": "errored",
            },
            "waiting_cookies": {
                "msg": "input your cookies",
                "got_cookies": "waiting_object",
                "reset": "initial",
                "error": "errored",
            },
            "waiting_object": {
                "msg": "input the object name",
                "got_object": "configured",
                "reset": "initial",
                "error": "errored",
            },
            "configured": {
                "msg": "service added successfully",
                "run": "running",
                "reset": "initial",
                "error": "errored",
            },
            "running": {
                "msg": "running",
                "reset": "initial",
                "error": "errored",
            }
        }

    def transition(self, input_str):
        if input_str in self.transitions[self.state]:
            print(f'Switching from the {self.state} to the {self.transitions[self.state][input_str]}')
            self.state = self.transitions[self.state][input_str]
            set_user_state(user_id=self.user.user_id, session=self.session, state=self.state)
            return self.transitions[self.state]['msg']
        return self.transitions[self.state]['error']

    def get_email(self, email):
        if self.state == "waiting_email":
            if add_user_email(self.session, self.user.user_id, email):
                return self.transition("got_email")

            return self.transition("error")

    def get_cookies(self, msg):
        if self.state == "waiting_cookies":
            objects = []
            if add_user_cookie(self.session, self.user.user_id, msg):
                service_objects = MyService(self.user.user_cookie, self.user.user_email)
                for person in service_objects.get_all_people():
                    objects.append(person.nickname)
                return self.transition("got_cookies"), objects

            return self.transition("error")

    def get_object(self, obj):
        if self.state == "waiting_object":
            if add_tracking_object(self.session, self.user.user_id, obj):
                return self.transition("got_object")

            return self.transition("error")

    def run(self, *args):
        if self.state == "initial":
            self.transition("locator")
            return "Starting locator registration procedure. \nSend me your email address."
        elif self.state == "waiting_email":
            return self.get_email(*args)
        elif self.state == "waiting_cookies":
            return self.get_cookies(*args)
        elif self.state == "waiting_object":
            return self.get_object(*args)
        elif self.state == "configured":
            return "Noted!"
        else:
            return False