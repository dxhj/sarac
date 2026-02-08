from sarac.frontend.ast import *
from sarac.frontend.parser import Parser
from sarac.frontend.printer import PrettyPrintASTVisitor

with open('examples/in.sra', 'r') as f:
    parser = Parser()
    program = parser.parse(f.read())

    if parser.error_count == 0:
        print("=" * 60)
        print("AST Pretty Print Output")
        print("=" * 60)
        pretty_printer = PrettyPrintASTVisitor()
        program.accept(pretty_printer)
    else:
        print(f"Parse errors: {parser.error_count}")

