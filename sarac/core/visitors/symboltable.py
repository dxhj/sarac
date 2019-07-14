from sarac.core.symbols.table import SymbolTable
from sarac.core.symbols.attributes import FunctionAttributes, VariableAttributes
from sarac.core.rep.ast import TranslationUnitList, FunctionDefinition,\
    CompoundStatement, Declaration, Assignment, Reference
from sarac.core.error import Error


class BuildSymbolTableVisitor(object):
    def __init__(self):
        self.symbol_table = SymbolTable()
        self.symbol_table.open_scope(self.symbol_table.global_scope)
        self.offset = 0  # Offsets are treated as indexes to facilitate target generation

    def visit(self, node):
        if isinstance(node, FunctionDefinition):
            attributes = FunctionAttributes()
            attributes.type = node.return_type
            attributes.name = node.children[0].name
            attributes.parameters = node.children[1]
            self.symbol_table.put(node.children[0], attributes)
            node.children[0].attributes = attributes
            self.offset = 0  # Reset offset
            self.symbol_table.open_scope()
            node.children[1].accept_children(self)
            node.children[2].accept_children(self)
            node.children[2].names = self.symbol_table.current_scope()
            self.symbol_table.close_scope()
            return

        elif isinstance(node, CompoundStatement):
            self.symbol_table.open_scope()

        elif isinstance(node, Declaration):
            attributes = VariableAttributes()
            attributes.type = node.type
            attributes.name = node.children[0].name
            attributes.offset = self.offset
            self.offset += 1
            self.symbol_table.put(node.children[0], attributes)

        elif isinstance(node, Assignment):
            attributes = self.symbol_table.lookup(node.children[0].name)
            node.children[0].attributes = attributes
            node.children[0].type = attributes.type

        elif isinstance(node, Reference):
            attributes = self.symbol_table.lookup(node.name)
            if attributes is None:
                Error.name_error("undeclared symbol \"%s\"" % node.name, node.coord.line, node.coord.column)
            else:
                node.type = attributes.type
                node.attributes = attributes

        node.accept_children(self)

        if isinstance(node, TranslationUnitList):
            node.names = self.symbol_table.global_scope

        elif isinstance(node, CompoundStatement):
            node.names = self.symbol_table.current_scope()
            self.symbol_table.close_scope()


class SymbolTablePrinterVisitor(object):
    def visit(self, node):
        if isinstance(node, TranslationUnitList):
            print "global symbol table"
            print "\t", node.names

        elif isinstance(node, CompoundStatement):
            print "compound statement"
            print "\t", node.names

        node.accept_children(self)
