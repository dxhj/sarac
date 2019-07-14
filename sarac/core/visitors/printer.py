from sarac.core.rep.ast import *


class PrintASTVisitor(object):
    def __init__(self):
        self.spaces = 0

    def visit(self, node):
        if isinstance(node, TranslationUnitList):
            print '* Visiting a translation unit list'
            node.accept_children(self)
        if isinstance(node, Declaration):
            self.spaces += 1
            print '* Visiting a declaration'
            node.accept_children(self)
            self.spaces -= 1
        elif isinstance(node, DeclarationList):
            self.spaces += 1
            print '* Visiting declarations'
            node.accept_children(self)
            self.spaces -= 1
        elif isinstance(node, ParameterList):
            self.spaces += 1
            print '* Visiting parameters'
            node.accept_children(self)
            self.spaces -= 1
        elif isinstance(node, StatementList):
            print '* Visiting statements'
            node.accept_children(self)
        elif isinstance(node, FunctionDefinition):
            print '* Visiting function definition'
            node.accept_children(self)
        elif isinstance(node, If):
            print '* Visiting if'
            node.accept_children(self)
        elif isinstance(node, While):
            print '* Visiting while'
            node.accept_children(self)
        elif isinstance(node, For):
            print '* Visiting for'
            node.accept_children(self)
        elif isinstance(node, CompoundStatement):
            print '* Visiting a compound statement'
            print 'Symbols: ', node.names
            node.accept_children(self)
        elif isinstance(node, Assignment):
            self.spaces += 1
            print '* Visiting an assignment'
            node.accept_children(self)
            self.spaces -= 1
        elif isinstance(node, UnaryOperator):
            print self.spaces * '\t', 'Visiting an unary operator', node.op
            node.accept_children(self)
        elif isinstance(node, BinaryOperator):
            print self.spaces * '\t', 'Visiting a binary operator: ', node.op
            node.accept_children(self)
        elif isinstance(node, Identifier):
            print self.spaces * '\t', "Visiting an identifier: ", node.name
        elif isinstance(node, Reference):
            print self.spaces * '\t', "Visiting a reference: ", node.name
        elif isinstance(node, Constant):
            print self.spaces * '\t', "Visiting a constant: ", node.value
