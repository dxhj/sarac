import ply.yacc as yacc

from sarac.frontend.lexer import Lexer, Coord
from sarac.analysis.types import *
from sarac.frontend.ast import *
from sarac.utils.error import Error


class Parser(object):
    precedence = (
        ('left', 'EQUAL', 'NOT_EQUAL'),
        ('left', 'LT', 'LE', 'GT', 'GE'),
        ('left', 'PLUS', 'MINUS'),
        ('left', 'TIMES', 'DIV'),
    )

    def __init__(self):
        self.error_count = 0
        self.lexer = Lexer()
        self.lexer.build(optimize=False, debug=True)
        self.tokens = self.lexer.tokens
        self.parser = yacc.yacc(module=self, optimize=False, debug=True)

    def parse(self, input_text):
        return self.parser.parse(input_text)

    def p_translation_unit(self, p):
        """translation_unit : external_declaration
                            | translation_unit external_declaration"""
        if len(p) == 3:
            p[0] = p[1]
            p[0].children.append(p[2])
        else:
            p[0] = TranslationUnitList([p[1]])

    def p_external_declaration(self, p):
        """external_declaration : function_definition
                                | declaration """
        p[0] = p[1]

    def p_function_definition(self, p):
        """function_definition : type_specifier IDENTIFIER LPAREN parameters RPAREN compound_statement"""
        identifier = Identifier(p[2][0])
        identifier.coord = Coord(p[2][1], p[2][2])
        p[0] = FunctionDefinition(identifier, p[1], p[4], p[6])


    def p_parameters(self, p):
        """parameters : parameter_list
                      | 
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = ParameterList([])

    def p_parameter_list(self, p):
        """parameter_list : parameter_list COMMA type_specifier IDENTIFIER
                          | type_specifier IDENTIFIER
        """

        if len(p) == 5:
            identifier = Identifier(p[4][0], p[3])
            identifier.coord = Coord(p[4][1], p[4][2])
            declaration = Declaration(p[3], identifier)
            declaration.coord = identifier.coord
            p[0] = p[1]
            p[0].children.append(declaration)
        else:
            identifier = Identifier(p[2][0], p[1])
            identifier.coord = Coord(p[2][1], p[2][2])
            declaration = Declaration(p[1], identifier)
            declaration.coord = identifier.coord
            p[0] = ParameterList([declaration])

    def p_declaration_list(self, p):
        """declarations : declarations declaration
                        |
        """
        if len(p) == 3:
            p[0] = p[1]
            p[0].children.append(p[2])
        else:
            p[0] = DeclarationList([])

    def p_declaration(self, p):
        """declaration : type_specifier IDENTIFIER SEMICOLON
                       | type_specifier IDENTIFIER ASSIGN expression SEMICOLON"""
        identifier = Identifier(p[2][0], p[1])
        identifier.coord = Coord(p[2][1], p[2][2])
        if len(p) == 6:
            # Declaration with initialization: type IDENTIFIER = expression;
            p[0] = Declaration(p[1], identifier, p[4])
        else:
            # Declaration without initialization: type IDENTIFIER;
            p[0] = Declaration(p[1], identifier)
        p[0].coord = identifier.coord

    def p_statement_list(self, p):
        """statements : statements statement
                      |
        """
        if len(p) == 3:
            p[0] = p[1]
            p[0].children.append(p[2])
        else:
            p[0] = StatementList([])

    def p_control_if(self, p):
        """statement : IF LPAREN expression RPAREN statement
                     | IF LPAREN expression RPAREN statement ELSE statement
        """
        if len(p) == 6:
            p[0] = If(p[3], p[5])
        else:
            p[0] = If(p[3], p[5], p[7])

    def p_while_loop(self, p):
        """statement : WHILE LPAREN expression RPAREN statement"""
        p[0] = While(p[3], p[5])

    def p_for_loop(self, p):
        """statement : FOR LPAREN expression_statement expression_statement RPAREN statement
                     | FOR LPAREN expression_statement expression_statement expression RPAREN statement"""

        if len(p) == 7:
            p[0] = For(p[3], p[4], None, p[6])
        else:
            p[0] = For(p[3], p[4], p[5], p[7])

    def p_assignment(self, p):
        """statement : IDENTIFIER ASSIGN expression SEMICOLON"""
        identifier = Identifier(p[1][0])
        identifier.coord = Coord(p[1][1], p[1][2])
        p[0] = Assignment(identifier, p[3])
        p[0].coord = identifier.coord

    def p_return_statement(self, p):
        """statement : RETURN SEMICOLON
                     | RETURN expression SEMICOLON"""
        if len(p) == 3:
            # return;
            p[0] = Return(None)
        else:
            # return expression;
            p[0] = Return(p[2])
        # Set coordinate from RETURN token (token value is tuple: (value, line, column))
        if isinstance(p[1], tuple) and len(p[1]) >= 3:
            p[0].coord = Coord(p[1][1], p[1][2])

    def p_compound_statement(self, p):
        """statement : compound_statement"""
        p[0] = p[1]

    def p_expression_statement(self, p):
        """statement : expression_statement"""
        p[0] = p[1]

    def p_compound(self, p):
        """compound_statement : LBRACE declarations statements RBRACE"""
        p[0] = CompoundStatement(p[2], p[3])

    def p_expression_semi(self, p):
        """expression_statement : SEMICOLON
                                | expression SEMICOLON"""
        if len(p) == 2:
            p[0] = None
        else:
            p[0] = p[1]

    def p_binary_expression(self, p):
        """expression : unary_expression
                      | expression EQUAL expression
                      | expression NOT_EQUAL expression
                      | expression LT expression
                      | expression LE expression
                      | expression GT expression
                      | expression GE expression
                      | expression PLUS expression
                      | expression MINUS expression
                      | expression TIMES expression 
                      | expression DIV expression"""
        if len(p) == 2:
            p[0] = p[1]
        else:
            binary_op = BinaryOperator(p[2][0], p[1], p[3])
            binary_op.coord = Coord(p[2][1], p[2][2])
            p[0] = binary_op

    def p_unary_expression(self, p):
        """unary_expression : primary_expression
                            | unary_operator unary_expression"""
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = UnaryOperator(p[1], p[2])

    def p_expression_paren(self, p):
        """primary_expression : LPAREN expression RPAREN"""
        p[0] = p[2]

    def p_primary_expression_number(self, p):
        """primary_expression : NUMBER"""
        if '.' in p[1][0]:
            p[0] = Constant(p[1][0], floatTypeDescriptor)
        else:
            p[0] = Constant(p[1][0], integerTypeDescriptor)

    def p_primary_expression_character(self, p):
        """primary_expression : CHARACTER_LITERAL"""
        # p[1] is a tuple: (char_value, line, column)
        # Create a Constant with charTypeDescriptor
        # Store the character as its ASCII value or as the character itself
        char_value = p[1][0]
        p[0] = Constant(char_value, charTypeDescriptor)
        p[0].coord = Coord(p[1][1], p[1][2])

    def p_primary_expression_string(self, p):
        """primary_expression : STRING_LITERAL"""
        # p[1] is a tuple: (string_value, line, column)
        # Create a Constant with stringTypeDescriptor
        string_value = p[1][0]
        p[0] = Constant(string_value, stringTypeDescriptor)
        p[0].coord = Coord(p[1][1], p[1][2])

    def p_primary_expression_ref(self, p):
        """primary_expression : IDENTIFIER"""
        reference = Reference(p[1][0])
        reference.coord = Coord(p[1][1], p[1][2])
        p[0] = reference

    def p_primary_expression_function_call(self, p):
        """primary_expression : IDENTIFIER LPAREN argument_list RPAREN"""
        identifier = Identifier(p[1][0])
        identifier.coord = Coord(p[1][1], p[1][2])
        function_call = FunctionCall(identifier, p[3])
        function_call.coord = identifier.coord
        p[0] = function_call

    def p_argument_list(self, p):
        """argument_list : expression_list
                        |"""
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = ArgumentList([])

    def p_expression_list(self, p):
        """expression_list : expression_list COMMA expression
                          | expression"""
        if len(p) == 4:
            # expression_list COMMA expression
            p[0] = p[1]
            p[0].children.append(p[3])
        else:
            # expression
            p[0] = ArgumentList([p[1]])

    def p_unary_operator(self, p):
        """unary_operator : NOT
                          | MINUS
                          | PLUS"""
        p[0] = p[1][0]

    def p_type_specifier(self, p):
        """type_specifier : CHAR
                          | INT
                          | FLOAT
                          | STRING"""
        if p[1][0] == "char":
            p[0] = charTypeDescriptor
        elif p[1][0] == "int":
            p[0] = integerTypeDescriptor
        elif p[1][0] == "float":
            p[0] = floatTypeDescriptor
        else:
            p[0] = stringTypeDescriptor

    def p_error(self, p):
        self.error_count += 1
        if p is not None:
            Error.syntax_error("unexpected token '%s'" % p.value[0],
                               p.value[1], p.value[2])

            while True:
                token = self.parser.token()
                if token is None \
                        or token.type == "SEMICOLON" \
                        or token.type == "LBRACE":
                    break

            self.parser.errok()
            return token
        else:
            Error.syntax_error("unexpected end-of-file")
