class HelperException(Exception): ...


class ClientNotStart(HelperException): ...


class GameEnd(HelperException):
    pass


class GameStart(HelperException):
    pass
