"""
Code generation module for compiling LLVM IR to executable.
"""

import os
import subprocess
import tempfile
import sys


class CodeGenerator:
    """Compiles LLVM IR to executable."""
    
    def __init__(self, output_file=None, save_llvm_ir=False):
        self.output_file = output_file
        self.save_llvm_ir = save_llvm_ir  # Whether to save .ll file
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
            print(f"To compile manually, use: clang {llvm_file} -o {output_name}")
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
        print(f"To compile manually, use: clang {llvm_file} -o {output_name}")
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
            
            # Compile with clang, linking against libc
            result = subprocess.run(
                ['clang', llvm_file, '-o', output_name, '-lc'],
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
            
            # Compile to assembly
            asm_file = llvm_file + '.s'
            result = subprocess.run(
                ['llc', llvm_file, '-o', asm_file],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return False
            
            # Assemble and link
            result = subprocess.run(
                ['gcc', asm_file, '-o', output_name],
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
    
    def cleanup(self):
        """Clean up temporary files."""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass
        self.temp_files = []

