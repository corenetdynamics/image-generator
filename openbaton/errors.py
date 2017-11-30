class _BaseException(Exception):
    def __init__(self, message, *args):
        super(_BaseException, self).__init__(*args)
        self.message = message


class MethodNotFound(_BaseException):
    pass


class ImageCreatedNotFound(_BaseException):
    pass


class ExecutionError(_BaseException):
    pass
