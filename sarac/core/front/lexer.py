import ply.lex as lex
from sarac.core.error import Error


class Coord(object):
    def __init__(self, line, column):
        self.line = line
        self.column = column


class Lexer(object):
    keywords = {
        'for':   'FOR',
        'while': 'WHILE',
        'do':    'DO',
        'if':    'IF',
        'else':  'ELSE',
        'char':  'CHAR',
        'int':   'INT',
        'float': 'FLOAT',
        'return': 'RETURN'
    }

    tokens = [
        'IDENTIFIER',
        'NUMBER',
        'LT',
        'LE',
        'GT',
        'GE',
        'PLUS',
        'MINUS',
        'TIMES',
        'DIV',
        'NOT',
        'LPAREN',
        'RPAREN',
        'LBRACKET',
        'RBRACKET',
        'LBRACE',
        'RBRACE',
        'COMMA',
        'SEMICOLON',
        'EQUAL',
        'NOT_EQUAL',
        'ASSIGN',
    ] + list(keywords.values())

    t_ignore = ' \t'

    def __init__(self):
        self.lexer = None

    def build(self, **kwargs):
        self.lexer = lex.lex(module=self, **kwargs)

    def token_column(self, t):
        last_cr = t.lexer.lexdata.rfind('\n', 0, t.lexpos)
        return t.lexpos - last_cr

    def t_NUMBER(self, t):
        r"""[0-9]+(\.[0-9]+)?"""
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_IDENTIFIER(self, t):
        r"""_*[a-zA-Z][_a-zA-Z0-9]*"""
        t.type = self.keywords.get(t.value, 'IDENTIFIER')
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_PLUS(self, t):
        r"""\+"""
        print(t)
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_MINUS(self, t):
        r"""\-"""
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_TIMES(self, t):
        r"""\*"""
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_DIV(self, t):
        r"""\/"""
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_NOT(self, t):
        r"""!"""
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_LT(self, t):
        r"""<"""
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_LE(self, t):
        r"""<="""
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_GT(self, t):
        r""">"""
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_GE(self, t):
        r""">="""
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_ASSIGN(self, t):
        r"""="""
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_EQUAL(self, t):
        r"""=="""
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_NOT_EQUAL(self, t):
        r"""!="""
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_LPAREN(self, t):
        r"""\("""
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_RPAREN(self, t):
        r"""\)"""
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_LBRACKET(self, t):
        r"""\["""
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_RBRACKET(self, t):
        r"""\]"""
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_LBRACE(self, t):
        r"""\{"""
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_RBRACE(self, t):
        r"""\}"""
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_COMMA(self, t):
        r""","""
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_SEMICOLON(self, t):
        r""";"""
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_NEWLINE(self, t):
        r"""\n+"""
        t.lexer.lineno += len(t.value)

    def t_error(self, t):
        Error.lexical_error("unknown char '%c'" % t.value[0], t.lexer.lineno, self.token_column(t))
        if len(t.value) > 1:
            print("\t\t", u'\u2304')
            print("\t>> \t", t.value[0:5].strip())
        t.lexer.skip(1)  # Skip one char ahead.
