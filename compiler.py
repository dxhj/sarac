from sarac.core.rep.ast import *

from sarac.core.front.parser import Parser
from sarac.core.visitors.symboltable import BuildSymbolTableVisitor, SymbolTablePrinterVisitor
from sarac.core.visitors.optimizer import OptimizerVisitor
from sarac.core.visitors.semantics import SemanticsVisitor
from sarac.core.visitors.printer import PrintASTVisitor

t_count = 0


class GenCode(object):
    t_count = 0

    def __init__(self):
        self.already = {}

    def visit(self, expression):
        if expression in self.already:
            return
        else:
            self.already[expression] = True

        if isinstance(expression, Constant):
            print "t{0} = {1}".format(GenCode.t_count, expression.value)
            expression.name = "t" + str(GenCode.t_count)
        elif isinstance(expression, Reference):
            GenCode.t_count -= 1
        elif isinstance(expression, UnaryOperator):
            if expression.op == '-':
                expression.accept_children(self)
                print "t{0} = neg {1}".format(GenCode.t_count, expression.children[0].name)
                expression.name = "t" + str(GenCode.t_count)
            elif expression.op == '+':
                expression.accept_children(self)
                expression.name = expression.children[0].name
        elif isinstance(expression, BinaryOperator):
            expression.children[0].accept(self)
            expression.children[1].accept(self)
            if expression.op == '+':
                print "t{0} = {1} + {2}".format(GenCode.t_count, expression.children[0].name,
                                                expression.children[1].name)

            elif expression.op == '-':

                print "t{0} = {1} - {2}".format(GenCode.t_count, expression.children[0].name,
                                                expression.children[1].name)
            elif expression.op == '*':
                print "t{0} = {1} * {2}".format(GenCode.t_count, expression.children[0].name,
                                                expression.children[1].name)
            elif expression.op == '/':
                print "t{0} = {1} / {2}".format(GenCode.t_count, expression.children[0].name,
                                                expression.children[1].name)
            expression.name = "t" + str(GenCode.t_count)
        elif isinstance(expression, Assignment):
            expression.children[1].accept(self)
            print "{0} = {1}".format(expression.children[0].name, expression.children[1].name)
        GenCode.t_count += 1

with open('in.sra', 'r') as f:
    parser = Parser()
    program = parser.parse(f.read())

    if parser.error_count == 0:
        printer = PrintASTVisitor()
        program.accept_children(printer)

        table = BuildSymbolTableVisitor()
        program.accept(table)

        semantics = SemanticsVisitor()
        program.accept_children(semantics)

        ast_optimizer = OptimizerVisitor()
        program.accept_children(ast_optimizer)

        program.accept_children(printer)

        """
        table = BuildSymbolTableVisitor()
        program.accept(table)

        symtab_printer = SymbolTablePrinter()
        program.accept(symtab_printer)
        """