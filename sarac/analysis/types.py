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


class StringTypeDescriptor(TypeDescriptor):
    def __init__(self):
        # Strings are pointers, so size is pointer size (typically 8 bytes on 64-bit)
        super(StringTypeDescriptor, self).__init__(8)

    def __repr__(self):
        return "string"


def is_numeric_type(ttype):
    """Check if a type is numeric. Returns True only for int, float, and char.
    String types are NOT numeric types."""
    if ttype == integerTypeDescriptor or ttype == floatTypeDescriptor or ttype == charTypeDescriptor:
        return True
    return False


def generalize_type(type1, type2):
    """Generalize two types for binary operations. Only works for numeric types.
    Returns None if either type is not numeric (e.g., string types).
    String types cannot be used in arithmetic operations."""
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
stringTypeDescriptor = StringTypeDescriptor()
