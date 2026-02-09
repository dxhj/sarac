#!/usr/bin/env python3
"""
Sarac Compiler - Main compiler driver.

This module orchestrates all phases of the compilation process:
1. Lexing and Parsing
2. Symbol Table Building
3. Semantic Analysis
4. AST Optimization
5. MIR Generation
6. MIR Optimization
7. Code Generation (LLVM IR, GAS assembly, or executable)
"""

import argparse
import os
import sys

from sarac.frontend.parser import Parser
from sarac.analysis.symboltable import BuildSymbolTableVisitor
from sarac.optimization.optimizer import OptimizerVisitor
from sarac.analysis.semantic import SemanticsVisitor
from sarac.frontend.printer import PrintASTVisitor
from sarac.ir.codegen import CodeGenerator
from sarac.utils.error import SaraErrorException

# Default input file
DEFAULT_INPUT_FILE = 'examples/in.sra'


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Sarac Compiler - Compile Sara source code',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.sra                    # Compile to executable
  %(prog)s input.sra --mir              # Save MIR representation
  %(prog)s input.sra --asm              # Save GAS assembly
  %(prog)s input.sra --ll                # Save LLVM IR
  %(prog)s input.sra -O2                 # Compile with optimization level 2
  %(prog)s input.sra --debug             # Enable debug output
        """
    )
    
    parser.add_argument(
        'input_file',
        nargs='?',
        default=DEFAULT_INPUT_FILE,
        help=f'Input Sara source file (default: {DEFAULT_INPUT_FILE})'
    )
    
    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        help='Enable debug output (show AST, MIR, LLVM IR)'
    )
    
    parser.add_argument(
        '--mir',
        action='store_true',
        help='Save MIR (Mid-level Intermediate Representation) to file'
    )
    
    parser.add_argument(
        '--asm', '--gas',
        dest='asm',
        action='store_true',
        help='Save GAS x86-64 assembly to file'
    )
    
    parser.add_argument(
        '--ll',
        action='store_true',
        help='Save LLVM IR to file'
    )
    
    parser.add_argument(
        '-O',
        dest='optimization_level',
        choices=['0', '1', '2', '3', 's', 'z'],
        default='1',
        help='Optimization level: 0 (none), 1 (default), 2, 3, s (size), z (size aggressive)'
    )
    
    args = parser.parse_args()
    
    # Check for optimization flags in sys.argv (handle -O0, -O1, etc.)
    for opt in ['-O0', '-O1', '-O2', '-O3', '-Os', '-Oz']:
        if opt in sys.argv:
            args.optimization_level = opt[1:]  # Remove the '-'
            break
    
    return args


def get_output_name(input_file):
    """Determine output name from input file."""
    output_name = os.path.splitext(os.path.basename(input_file))[0]
    if not output_name:
        output_name = "a.out"
    return output_name


def compile_phase_parser(input_file, debug=False):
    """Phase 1: Lexing and Parsing."""
    with open(input_file, 'r') as f:
        parser = Parser(debug=debug)
        program = parser.parse(f.read())
        
        if parser.error_count > 0:
            sys.exit(1)
        
        return program


def compile_phase_analysis(program, debug=False):
    """Phase 2: Symbol Table Building and Semantic Analysis."""
    # Symbol table building
    table = BuildSymbolTableVisitor()
    program.accept(table)
    
    # Semantic analysis
    semantics = SemanticsVisitor()
    program.accept_children(semantics)
    
    # Print AST in debug mode
    if debug:
        printer = PrintASTVisitor()
        program.accept_children(printer)
    
    return program


def compile_phase_optimization(program):
    """Phase 3: AST Optimization."""
    ast_optimizer = OptimizerVisitor()
    program.accept_children(ast_optimizer)
    return program


def compile_phase_mir(program, debug=False):
    """Phase 4: MIR Generation."""
    from sarac.ir.mir import MIRGenerator
    
    mir_generator = MIRGenerator()
    program.accept(mir_generator)
    
    if debug:
        print("\n" + "=" * 60)
        print("Generated MIR (before optimization)")
        print("=" * 60)
        for mir_func in mir_generator.functions:
            print(mir_func)
            print()
    
    return mir_generator


def compile_phase_mir_optimization(mir_generator, debug=False):
    """Phase 5: MIR Optimization."""
    from sarac.ir.mir_optimizer import optimize_mir
    
    for mir_func in mir_generator.functions:
        optimize_mir(mir_func)
    
    if debug:
        print("\n" + "=" * 60)
        print("Optimized MIR")
        print("=" * 60)
        for mir_func in mir_generator.functions:
            print(mir_func)
            print()
    
    return mir_generator


def save_mir_output(mir_generator, output_name):
    """Save MIR representation to file."""
    mir_file = output_name + ".mir"
    with open(mir_file, 'w') as f:
        for mir_func in mir_generator.functions:
            f.write(str(mir_func))
            f.write("\n\n")
    print(f"\n✓ MIR saved to {mir_file}")
    sys.exit(0)


def save_asm_output(mir_generator, output_name):
    """Save GAS assembly to file."""
    from sarac.ir.gas import GASGenerator
    
    gas_generator = GASGenerator()
    asm_code = gas_generator.generate(mir_generator.functions)
    asm_file = output_name + ".s"
    
    with open(asm_file, 'w') as f:
        f.write(asm_code)
    
    print(f"\n✓ Assembly saved to {asm_file}")
    sys.exit(0)


def compile_phase_codegen(mir_generator, output_name, save_llvm_ir=False, 
                          optimization_level='1', debug=False):
    """Phase 6: Code Generation (LLVM IR or Executable)."""
    from sarac.ir.llvm import LLVMGenerator
    
    llvm_generator = LLVMGenerator()
    llvm_ir = llvm_generator.generate(mir_generator.functions)
    
    if debug:
        print("\n" + "=" * 60)
        print("Generated LLVM IR")
        print("=" * 60)
        print(llvm_ir)
    
    codegen = CodeGenerator(save_llvm_ir=save_llvm_ir, optimization_level=optimization_level)
    executable_path = codegen.compile(llvm_ir, output_name)
    
    if executable_path:
        print(f"\n✓ Executable created: {executable_path}")
    elif not save_llvm_ir:
        print("\n✗ Could not create executable.")
        print("Use --ll flag to save LLVM IR to a file.")
        sys.exit(1)
    
    codegen.cleanup()


def main():
    """Main compiler entry point."""
    args = parse_arguments()
    
    # Validate input file
    if not os.path.exists(args.input_file):
        print(f"Error: File not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Phase 1: Parsing
        program = compile_phase_parser(args.input_file, debug=args.debug)
        
        # Phase 2: Analysis
        program = compile_phase_analysis(program, debug=args.debug)
        
        # Phase 3: AST Optimization
        program = compile_phase_optimization(program)
        
        # Phase 4: MIR Generation
        mir_generator = compile_phase_mir(program, debug=args.debug)
        
        # Phase 5: MIR Optimization
        mir_generator = compile_phase_mir_optimization(mir_generator, debug=args.debug)
        
        # Determine output name
        output_name = get_output_name(args.input_file)
        
        # Handle intermediate output formats
        if args.mir:
            save_mir_output(mir_generator, output_name)
        
        if args.asm:
            save_asm_output(mir_generator, output_name)
        
        # Phase 6: Code Generation
        compile_phase_codegen(
            mir_generator,
            output_name,
            save_llvm_ir=args.ll,
            optimization_level=args.optimization_level,
            debug=args.debug
        )
    
    except SaraErrorException:
        # Error already printed by error handler
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error: File not found: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nCompilation interrupted by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: Unexpected error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
