class Node(object):
    def __init__(self):
        self.coord = None
        self.children = []

    def __iter__(self):
        for child in self.children:
            yield child

    def accept(self, visitor):
        visitor.visit(self)

    def accept_children(self, visitor):
        for child in self.children:
            child.accept(visitor) if child is not None else None


class Program(object):
    def __init__(self, statements):
        self.children = [statements]


class TranslationUnitList(Node):
    def __init__(self, units):
        super(TranslationUnitList, self).__init__()
        self.children = units


class FunctionDefinition(Node):
    def __init__(self, name, type, parameters, body):
        super(FunctionDefinition, self).__init__()
        self.children = [name, parameters, body]
        self.return_type = type
        # self.type = type
        # self.parameters = parameters
        # self.body = body


class ParameterList(Node):
    def __init__(self, parameters):
        super(ParameterList, self).__init__()
        self.children = parameters


class CompoundStatement(Node):
    def __init__(self, declaration_list, statement_list):
        super(CompoundStatement, self).__init__()
        self.children = [declaration_list, statement_list]
        self.names = {}


class StatementList(Node):
    def __init__(self, statements):
        super(StatementList, self).__init__()
        self.children = statements


class While(Node):
    def __init__(self, expression, statement):
        super(While, self).__init__()
        self.children = [expression, statement]


class For(Node):
    def __init__(self, init, condition, after, statement):
        super(For, self).__init__()
        self.children = [init, condition, after, statement]
        # self.init = init
        # self.condition = condition
        # self.after = after
        # self.statement = statement


class If(Node):
    def __init__(self, expression, then_part, else_part=None):
        super(If, self).__init__()
        self.children = [expression, then_part, else_part]

        # self.expression = expression
        # self.then_part = then_part
        # self.else_part = else_part


class Declaration(Node):
    def __init__(self, id_type, identifier, initializer=None):
        super(Declaration, self).__init__()
        if initializer is not None:
            self.children = [identifier, initializer]
        else:
            self.children = [identifier]
        self.type = id_type
        self.initializer = initializer
        # self.identifier = identifier
        # self.identifier.type = id_type


class DeclarationList(Node):
    def __init__(self, declarations):
        super(DeclarationList, self).__init__()
        self.children = declarations


class Assignment(Node):
    def __init__(self, identifier, expression):
        super(Assignment, self).__init__()
        self.type = None
        self.children = [identifier, expression]


class Expression(Node):
    def __init__(self):
        super(Expression, self).__init__()
        self.name = None
        self.type = None


class UnaryOperator(Expression):
    UNARY_OP = 1

    def __init__(self, operator, expression):
        super(UnaryOperator, self).__init__()
        self.op = operator
        self.children = [expression]

    def __repr__(self):
        return "%s(%s)" % (self.op, str(self.children[0]))


class BinaryOperator(Expression):
    BINARY_OP = 1

    def __init__(self, operator, left_expression, right_expression):
        super(BinaryOperator, self).__init__()
        self.op = operator
        self.children = [left_expression, right_expression]

    def __repr__(self):
        return "%s %s %s" % (str(self.children[0]), self.op, str(self.children))


class Constant(Expression):
    CONSTANT = 2

    def __init__(self, value, ctype):
        super(Constant, self).__init__()
        self.type = ctype
        self.value = value

    def __repr__(self):
        return self.value


class Reference(Expression):
    REFERENCE = 3

    def __init__(self, name):
        super(Reference, self).__init__()
        self.name = name
        self.attributes = None

    def __repr__(self):
        return self.name


class Identifier(Node):
    IDENTIFIER = 3

    def __init__(self, name, id_type=None, value=None):
        super(Identifier, self).__init__()
        self.name = name
        self.type = id_type
        self.value = value
        self.attributes = None


class Return(Node):
    def __init__(self, expression=None):
        super(Return, self).__init__()
        if expression is not None:
            self.children = [expression]
        else:
            self.children = []
        self.expression = expression
