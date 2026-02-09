import ply.lex as lex
from sarac.utils.error import Error


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
        'string': 'STRING',
        'return': 'RETURN'
    }

    tokens = [
        'IDENTIFIER',
        'NUMBER',
        'CHARACTER_LITERAL',
        'STRING_LITERAL',
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
        'COLON',
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

    def t_CHARACTER_LITERAL(self, t):
        r"""'([^'\\]|\\.)'"""
        # Extract the character value, handling escape sequences
        char_content = t.value[1:-1]  # Remove quotes
        
        # Handle escape sequences
        if len(char_content) == 2 and char_content[0] == '\\':
            escape_char = char_content[1]
            escape_map = {
                'n': '\n',
                't': '\t',
                'r': '\r',
                '\\': '\\',
                "'": "'",
                '"': '"',
                '0': '\0'
            }
            char_value = escape_map.get(escape_char, escape_char)
        else:
            char_value = char_content
        
        # Store the character value as a string (single character)
        t.value = (char_value, t.lineno, self.token_column(t))
        return t

    def t_STRING_LITERAL(self, t):
        r'''"([^"\\]|\\.)*"'''
        # Extract the string value, handling escape sequences
        string_content = t.value[1:-1]  # Remove quotes
        
        # Process escape sequences
        result = []
        i = 0
        while i < len(string_content):
            if string_content[i] == '\\' and i + 1 < len(string_content):
                escape_char = string_content[i + 1]
                escape_map = {
                    'n': '\n',
                    't': '\t',
                    'r': '\r',
                    '\\': '\\',
                    "'": "'",
                    '"': '"',
                    '0': '\0'
                }
                result.append(escape_map.get(escape_char, escape_char))
                i += 2
            else:
                result.append(string_content[i])
                i += 1
        
        string_value = ''.join(result)
        t.value = (string_value, t.lineno, self.token_column(t))
        return t

    def t_IDENTIFIER(self, t):
        r"""_*[a-zA-Z][_a-zA-Z0-9]*"""
        t.type = self.keywords.get(t.value, 'IDENTIFIER')
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_PLUS(self, t):
        r"""\+"""
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

    # Order matters: longer patterns must come before shorter ones
    def t_LE(self, t):
        r"""<="""
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_GE(self, t):
        r""">="""
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

    def t_LT(self, t):
        r"""<"""
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_GT(self, t):
        r""">"""
        t.value = (t.value, t.lineno, self.token_column(t))
        return t

    def t_ASSIGN(self, t):
        r"""="""
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

    def t_COLON(self, t):
        r""":"""
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
