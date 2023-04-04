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