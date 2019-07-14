# from ..rep.ast import *

CHAR_SIZE = 1
INTEGER_SIZE = 4
FLOAT_SIZE = 8


class TypeDescriptor(object):
    def __init__(self, size):
        self.size = size


class CharTypeDescriptor(TypeDescriptor):
    def __init__(self):
        super(CharTypeDescriptor, self).__init__(CHAR_SIZE)

    def __repr__(self):
        return "char"


class IntegerTypeDescriptor(TypeDescriptor):
    def __init__(self):
        super(IntegerTypeDescriptor, self).__init__(INTEGER_SIZE)

    def __repr__(self):
        return "int"


class FloatTypeDescriptor(TypeDescriptor):
    def __init__(self):
        super(FloatTypeDescriptor, self).__init__(FLOAT_SIZE)

    def __repr__(self):
        return "float"


def is_numeric_type(ttype):
    if ttype == integerTypeDescriptor or ttype == floatTypeDescriptor or ttype == charTypeDescriptor:
        return True
    return False


def generalize_type(type1, type2):
    if not is_numeric_type(type1) or not is_numeric_type(type2):
        return None
    if type1 == floatTypeDescriptor or type2 == floatTypeDescriptor:
        return floatTypeDescriptor
    elif type1 == integerTypeDescriptor or type2 == integerTypeDescriptor:
        return integerTypeDescriptor
    return charTypeDescriptor


charTypeDescriptor = CharTypeDescriptor()
integerTypeDescriptor = IntegerTypeDescriptor()
floatTypeDescriptor = FloatTypeDescriptor()
