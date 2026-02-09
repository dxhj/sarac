from sarac.frontend.ast import *
import os
import sys

from sarac.frontend.parser import Parser
from sarac.analysis.symboltable import BuildSymbolTableVisitor, SymbolTablePrinterVisitor
from sarac.optimization.optimizer import OptimizerVisitor
from sarac.analysis.semantic import SemanticsVisitor
from sarac.frontend.printer import PrintASTVisitor
from sarac.ir.codegen import CodeGenerator


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
        
        # Print MIR for each function (before optimization)
        print("\n" + "=" * 60)
        print("Generated MIR (before optimization)")
        print("=" * 60)
        for mir_func in mir_generator.functions:
            print(mir_func)
            print()
        
        # Optimize MIR
        from sarac.ir.mir_optimizer import optimize_mir
        for mir_func in mir_generator.functions:
            optimize_mir(mir_func)
        
        # Print MIR for each function (after optimization)
        print("\n" + "=" * 60)
        print("Optimized MIR")
        print("=" * 60)
        for mir_func in mir_generator.functions:
            print(mir_func)
            print()
        
        # Generate LLVM IR
        from sarac.ir.llvm import LLVMGenerator
        llvm_generator = LLVMGenerator()
        llvm_ir = llvm_generator.generate(mir_generator.functions)
        
        print("\n" + "=" * 60)
        print("Generated LLVM IR")
        print("=" * 60)
        print(llvm_ir)
        
        # Determine output name from input file
        input_file = 'examples/in.sra'
        output_name = os.path.splitext(os.path.basename(input_file))[0]
        if not output_name:
            output_name = "a.out"
        
        # Check if user wants to save .ll file (via command line argument)
        save_llvm_ir = '--ll' in sys.argv
        
        # Get optimization level from command line (default: '1')
        optimization_level = '1'
        if '-O0' in sys.argv:
            optimization_level = '0'
        elif '-O1' in sys.argv:
            optimization_level = '1'
        elif '-O2' in sys.argv:
            optimization_level = '2'
        elif '-O3' in sys.argv:
            optimization_level = '3'
        elif '-Os' in sys.argv:
            optimization_level = 's'
        elif '-Oz' in sys.argv:
            optimization_level = 'z'
        
        codegen = CodeGenerator(save_llvm_ir=save_llvm_ir, optimization_level=optimization_level)
        executable_path = codegen.compile(llvm_ir, output_name)
        
        if executable_path:
            print(f"\n✓ Executable created: {executable_path}")
        elif not save_llvm_ir:
            print("\n✗ Could not create executable.")
            print("Use --ll flag to save LLVM IR to a file.")
        
        codegen.cleanup()