import sys


def error(func):
    def error_wrapper(cls, msg, line=None, column=None):
        # Stop on first error
        Error.errors += 1
        if line is None:
            error_msg = func(cls, msg)
        else:
            error_msg = func(cls, msg, line, column)
        print(error_msg)
        # Exit immediately on first error
        raise SaraErrorException(error_msg)
    return error_wrapper


class SaraErrorException(Exception):
    pass


class Error(object):
    errors = 0

    @classmethod
    @error
    def syntax_error(cls, msg, line=None, column=None):
        if line is None:
            return "syntax error: %s" % msg
        return "syntax error: %s [%d:%d]" % (msg, line, column)

    @classmethod
    @error
    def name_error(cls, msg, line, column):
        return "name error: %s [%d:%d]" % (msg, line, column)

    @classmethod
    @error
    def lexical_error(cls, msg, line, column):
        return "lexical error: %s [%d:%d]" % (msg, line, column)

    @classmethod
    @error
    def type_error(cls, msg, line, column):
        return "type error: %s [%d:%d]" % (msg, line, column)
