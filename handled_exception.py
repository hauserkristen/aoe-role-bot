import sys
import traceback

class HandeledException(Exception):
    def __init__(self, previous_exception):
        Exception.__init__(previous_exception)

        exception_type, exception, exception_traceback = sys.exc_info()

        if exception is not None:
            self.exception = exception
        else:
            self.exception = previous_exception
        if exception_type is None:
            self.exception_name = exception_type.__name__
        else:
            self.exception_name = type(previous_exception).__name__
        if exception_traceback is None:
            self.stack = traceback.extract_tb(exception_traceback)
        else:
            self.stack = []


    def print_exception(self):
        return '{}: {}\n\nBacktrace: {}'.format(self.exception_name, self.exception, self.stack)