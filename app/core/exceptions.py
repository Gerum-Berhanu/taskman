"""Application-level exceptions (mapped to HTTP in the API layer)."""


class EmailAlreadyRegisteredError(Exception):
    pass
