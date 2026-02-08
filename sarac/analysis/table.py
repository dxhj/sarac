from sarac.utils.error import Error


class SymbolTable(object):
    def __init__(self):
        self.depth = 0
        self.global_scope = {}
        self.scope_stack = []

    def open_scope(self, scope=None):
        if scope is None:
            self.scope_stack.append({})
        else:
            self.scope_stack.append(scope)

    def close_scope(self):
        assert len(self.scope_stack) > 0
        self.scope_stack.pop()

    def current_scope(self):
        assert len(self.scope_stack) > 0
        return self.scope_stack[-1]

    def put(self, symbol, attributes):
        check_attr = self.lookup(symbol.name)
        if symbol.name in self.scope_stack[-1]:
            Error.name_error("\"%s\" is already defined" % symbol.name, symbol.coord.line, symbol.coord.column)
        elif check_attr is not None and type(check_attr) != type(attributes):
            Error.name_error("\"%s\" redeclared as different kind of symbol" % symbol.name,
                             symbol.coord.line,
                             symbol.coord.column)
        else:
            self.scope_stack[-1][symbol.name] = attributes

    def lookup(self, name):
        for scope in reversed(self.scope_stack):
            if name in scope:
                return scope[name]
        return None
