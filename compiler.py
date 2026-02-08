from sarac.frontend.ast import *

from sarac.frontend.parser import Parser
from sarac.analysis.symboltable import BuildSymbolTableVisitor, SymbolTablePrinterVisitor
from sarac.optimization.optimizer import OptimizerVisitor
from sarac.analysis.semantic import SemanticsVisitor
from sarac.frontend.printer import PrintASTVisitor

t_count = 0

with open('examples/in.sra', 'r') as f:
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

        # Generate MIR (Mid-level Intermediate Representation)
        from sarac.ir.mir import MIRGenerator
        mir_generator = MIRGenerator()
        program.accept(mir_generator)
        
        # Print MIR for each function
        print("\n" + "=" * 60)
        print("Generated MIR")
        print("=" * 60)
        for mir_func in mir_generator.functions:
            print(mir_func)
            print()