from sarac.frontend.ast import *
import os
import sys

from sarac.frontend.parser import Parser
from sarac.analysis.symboltable import BuildSymbolTableVisitor, SymbolTablePrinterVisitor
from sarac.optimization.optimizer import OptimizerVisitor
from sarac.analysis.semantic import SemanticsVisitor
from sarac.frontend.printer import PrintASTVisitor
from sarac.ir.codegen import CodeGenerator


from sarac.utils.error import SaraErrorException

try:
    # Get input file from command line or use default
    input_file = 'examples/in.sra'
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        input_file = sys.argv[1]
    
    # Check if debug mode is enabled (check early for parser debug output)
    debug = '--debug' in sys.argv or '-d' in sys.argv
    
    with open(input_file, 'r') as f:
        parser = Parser(debug=debug)
        program = parser.parse(f.read())

        # Stop if parsing errors occurred
        if parser.error_count > 0:
            sys.exit(1)

        # Print AST only in debug mode
        if debug:
            printer = PrintASTVisitor()
            program.accept_children(printer)

        # Symbol table building - will raise SaraErrorException on first error
        table = BuildSymbolTableVisitor()
        program.accept(table)

        # Semantic analysis - will raise SaraErrorException on first error
        semantics = SemanticsVisitor()
        program.accept_children(semantics)

        ast_optimizer = OptimizerVisitor()
        program.accept_children(ast_optimizer)

        # Generate MIR (Mid-level Intermediate Representation)
        from sarac.ir.mir import MIRGenerator
        mir_generator = MIRGenerator()
        program.accept(mir_generator)
        
        # Print MIR for each function (before optimization) only in debug mode
        if debug:
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
        
        # Print MIR for each function (after optimization) only in debug mode
        if debug:
            print("\n" + "=" * 60)
            print("Optimized MIR")
            print("=" * 60)
            for mir_func in mir_generator.functions:
                print(mir_func)
                print()
        
        # Determine output name from input file
        output_name = os.path.splitext(os.path.basename(input_file))[0]
        if not output_name:
            output_name = "a.out"
        
        # Check if user wants to save .mir file (via command line argument)
        save_mir = '--mir' in sys.argv
        
        # If user wants to save MIR, do that and exit
        if save_mir:
            mir_file = output_name + ".mir"
            with open(mir_file, 'w') as f:
                for mir_func in mir_generator.functions:
                    f.write(str(mir_func))
                    f.write("\n\n")
            print(f"\n✓ MIR saved to {mir_file}")
            sys.exit(0)
        
        # Check if user wants to save .s (assembly) file (via command line argument)
        save_asm = '--asm' in sys.argv or '--gas' in sys.argv
        
        # If user wants to save assembly, do that and exit
        if save_asm:
            from sarac.ir.gas import GASGenerator
            gas_generator = GASGenerator()
            asm_code = gas_generator.generate(mir_generator.functions)
            asm_file = output_name + ".s"
            with open(asm_file, 'w') as f:
                f.write(asm_code)
            print(f"\n✓ Assembly saved to {asm_file}")
            sys.exit(0)
        
        # Generate LLVM IR
        from sarac.ir.llvm import LLVMGenerator
        llvm_generator = LLVMGenerator()
        llvm_ir = llvm_generator.generate(mir_generator.functions)
        
        # Print LLVM IR only in debug mode
        if debug:
            print("\n" + "=" * 60)
            print("Generated LLVM IR")
            print("=" * 60)
            print(llvm_ir)
        
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
            sys.exit(1)
        
        codegen.cleanup()

except SaraErrorException:
    # Error already printed by error handler
    sys.exit(1)
except FileNotFoundError as e:
    print(f"Error: File not found: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error: Unexpected error: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)