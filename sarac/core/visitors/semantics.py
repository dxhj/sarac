from sarac.core.rep.ast import Reference, BinaryOperator, Assignment
from sarac.core.symbols.attributes import VariableAttributes
from sarac.core.symbols.types import generalize_type
from sarac.core.error import Error


class SemanticsVisitor(object):
    def visit(self, node):
        if isinstance(node, Reference):
            if node.attributes is not None and not is_data_object(node):
                Error.type_error("\"%s\" does not name a data object" % node.name, node.coord.line, node.coord.column)

        if isinstance(node, BinaryOperator):
            node.accept_children(self)
            node.type = generalize_type(node.children[0].type, node.children[1].type)

            if node.type is None:
                Error.type_error("invalid types", node.coord.line, node.coord.column)

            return

        if isinstance(node, Assignment):
            node.children[1].accept(self)
            if node.children[0].type is not node.children[1].type:
                Error.type_error("trying to assign different types", node.coord.line, node.coord.column)

            return

        node.accept_children(self)


def is_data_object(node):
    return type(node.attributes) == VariableAttributes
