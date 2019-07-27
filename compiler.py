from sarac.core.rep.ast import *

from sarac.core.front.parser import Parser
from sarac.core.visitors.symboltable import BuildSymbolTableVisitor, SymbolTablePrinterVisitor
from sarac.core.visitors.optimizer import OptimizerVisitor
from sarac.core.visitors.semantics import SemanticsVisitor
from sarac.core.visitors.printer import PrintASTVisitor

t_count = 0

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