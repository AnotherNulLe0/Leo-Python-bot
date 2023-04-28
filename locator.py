from locationsharinglib import Service
from locationsharinglib.locationsharinglibexceptions import InvalidCookies


class MyService(Service):
    def _get_authenticated_session(self, cookies_file):
        try:
            session = self._get_session_from_cookie_file(cookies_file)
        except FileNotFoundError:
            message = 'Could not open cookies file, either file does not exist or no read access.'
            raise InvalidCookies(message) from None
        return session

