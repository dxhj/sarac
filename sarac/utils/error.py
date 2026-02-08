import sys


def error(func):
    def error_wrapper(cls, msg, line=None, column=None):
        if Error.errors == 5:
            try:
                raise SaraErrorException()
            except SaraErrorException as e:
                if line is None:
                    print(func(cls, msg))
                else:
                    print(func(cls, msg, line, column))
                sys.exit(e)
        else:
            Error.errors += 1
            print(func(cls, msg, line, column))
    return error_wrapper


class SaraErrorException(Exception):
    pass


class Error(object):
    errors = 1

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
