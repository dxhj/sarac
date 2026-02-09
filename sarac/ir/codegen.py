"""
Code generation module for compiling LLVM IR to executable.
"""

import os
import subprocess
import tempfile
import sys


class CodeGenerator:
    """Compiles LLVM IR to executable."""
    
    def __init__(self, output_file=None, save_llvm_ir=False, optimization_level='1'):
        """
        Initialize the code generator.
        
        Args:
            output_file: Optional output file path
            save_llvm_ir: Whether to save .ll file instead of compiling
            optimization_level: Optimization level ('0', '1', '2', '3', 's', 'z')
                - '0': No optimization
                - '1': Basic optimizations (default)
                - '2': More aggressive optimizations
                - '3': Maximum optimizations
                - 's': Optimize for size
                - 'z': Optimize aggressively for size
        """
        self.output_file = output_file
        self.save_llvm_ir = save_llvm_ir  # Whether to save .ll file
        self.optimization_level = optimization_level
        self.temp_files = []  # Track temp files for cleanup
    
    def compile(self, llvm_ir, output_name="a.out"):
        """
        Compile LLVM IR to an executable.
        
        Args:
            llvm_ir: String containing LLVM IR code
            output_name: Name of the output executable
        
        Returns:
            Path to the compiled executable, or None if compilation failed or skipped
        """
        # If save_llvm_ir is requested, only save the .ll file and skip compilation
        if self.save_llvm_ir:
            llvm_file = output_name + ".ll"
            with open(llvm_file, 'w') as f:
                f.write(llvm_ir)
            print(f"\n✓ LLVM IR saved to {llvm_file}")
            opt_flag = self._get_clang_opt_flag()
            print(f"To compile manually, use: clang {llvm_file} -o {output_name} {opt_flag}")
            return None
        
        # Try different compilation methods
        if self._try_clang(llvm_ir, output_name):
            return os.path.abspath(output_name)
        
        if self._try_llc(llvm_ir, output_name):
            return os.path.abspath(output_name)
        
        # If all methods fail, optionally save LLVM IR to file
        llvm_file = output_name + ".ll"
        with open(llvm_file, 'w') as f:
            f.write(llvm_ir)
        print(f"\nWarning: Could not compile to executable. LLVM IR saved to {llvm_file}")
        opt_flag = self._get_clang_opt_flag()
        print(f"To compile manually, use: clang {llvm_file} -o {output_name} {opt_flag}")
        return None
    
    def _try_clang(self, llvm_ir, output_name):
        """Try to compile using clang."""
        try:
            # Check if clang is available
            result = subprocess.run(['which', 'clang'], 
                                  capture_output=True, 
                                  text=True)
            if result.returncode != 0:
                return False
            
            # Write LLVM IR to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ll', delete=False) as f:
                f.write(llvm_ir)
                llvm_file = f.name
                self.temp_files.append(llvm_file)
            
            # Build clang command with optimization flags
            clang_cmd = ['clang', llvm_file, '-o', output_name, '-lc']
            
            # Add optimization flag
            opt_flag = self._get_clang_opt_flag()
            if opt_flag:
                clang_cmd.append(opt_flag)
            
            # Compile with clang, linking against libc
            result = subprocess.run(
                clang_cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"\n✓ Successfully compiled to {output_name}")
                return True
            else:
                print(f"\n✗ Clang compilation failed:")
                print(result.stderr)
                return False
                
        except Exception as e:
            return False
    
    def _try_llc(self, llvm_ir, output_name):
        """Try to compile using llc (LLVM compiler)."""
        try:
            # Check if llc is available
            result = subprocess.run(['which', 'llc'], 
                                  capture_output=True, 
                                  text=True)
            if result.returncode != 0:
                return False
            
            # Write LLVM IR to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ll', delete=False) as f:
                f.write(llvm_ir)
                llvm_file = f.name
                self.temp_files.append(llvm_file)
            
            # Compile to assembly with optimization flags
            asm_file = llvm_file + '.s'
            llc_cmd = ['llc', llvm_file, '-o', asm_file]
            
            # Add optimization flag for llc
            opt_flag = self._get_llc_opt_flag()
            if opt_flag:
                llc_cmd.append(opt_flag)
            
            result = subprocess.run(
                llc_cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return False
            
            # Assemble and link with optimization flags
            gcc_cmd = ['gcc', asm_file, '-o', output_name]
            
            # Add optimization flag for gcc
            opt_flag = self._get_clang_opt_flag()  # GCC uses same flags as clang
            if opt_flag:
                gcc_cmd.append(opt_flag)
            
            result = subprocess.run(
                gcc_cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"\n✓ Successfully compiled to {output_name}")
                return True
            else:
                print(f"\n✗ GCC linking failed:")
                print(result.stderr)
                return False
                
        except Exception as e:
            return False
    
    def _get_clang_opt_flag(self):
        """Get clang/gcc optimization flag based on optimization level."""
        opt_map = {
            '0': '-O0',
            '1': '-O1',
            '2': '-O2',
            '3': '-O3',
            's': '-Os',  # Optimize for size
            'z': '-Oz',  # Optimize aggressively for size
        }
        return opt_map.get(self.optimization_level, '-O1')
    
    def _get_llc_opt_flag(self):
        """Get llc optimization flag based on optimization level."""
        # llc uses -O0, -O1, -O2, -O3 (no -Os or -Oz)
        opt_map = {
            '0': '-O0',
            '1': '-O1',
            '2': '-O2',
            '3': '-O3',
            's': '-O2',  # Map size optimization to O2 for llc
            'z': '-O2',  # Map aggressive size optimization to O2 for llc
        }
        return opt_map.get(self.optimization_level, '-O1')
    
    def cleanup(self):
        """Clean up temporary files."""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass
        self.temp_files = []

