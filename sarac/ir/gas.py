"""
GAS (GNU Assembler) x86-64 code generator for the Sarac compiler.

Converts MIR (Mid-level Intermediate Representation) to x86-64 assembly code.
Uses System V ABI calling convention for Linux.
"""

from sarac.ir.mir import MIRFunction, BasicBlock, Instruction, Op


class GASGenerator:
    """Converts MIR to GAS x86-64 assembly."""
    
    def __init__(self):
        self.output = []  # List of output lines
        self.temp_to_reg = {}  # Map MIR temps to registers/stack locations
        self.var_to_stack = {}  # Map variable names to stack offsets
        self.label_map = {}  # Map MIR block labels to assembly labels
        self.current_function = None
        self.stack_offset = 0  # Current stack offset for local variables
        self.max_stack_offset = 0  # Maximum stack offset used
        self.temp_counter = 0  # Counter for temporary stack slots
        self.string_literals = {}  # Map string values to label names
        self.string_counter = 0  # Counter for string literal labels
        self.reg_allocator = RegisterAllocator()
        self.pending_params = []  # Parameters collected before a CALL
        self.has_return = False  # Track if function has explicit return
    
    def emit(self, line):
        """Emit a line of assembly code."""
        self.output.append(line)
    
    def generate(self, mir_functions):
        """Generate GAS assembly for a list of MIR functions."""
        self.output = []
        self.string_literals = {}
        self.string_counter = 0
        
        # Emit header
        self.emit(".text")
        self.emit("")
        
        # Declare external functions
        self.emit(".extern printf")
        self.emit("")
        
        # First pass: collect all string literals
        for func in mir_functions:
            for block in func.blocks:
                for instr in block.instructions:
                    if instr.op == Op.CONST and instr.operands:
                        value = instr.operands[0]
                        # Check if it's a string type
                        is_string_type = False
                        if hasattr(instr, 'operand_types') and instr.operand_types and len(instr.operand_types) > 0:
                            type_str = str(instr.operand_types[0]).lower()
                            is_string_type = (type_str == "string")
                        
                        # If it's a string type, or if it's a multi-character string that's not numeric
                        if is_string_type or (isinstance(value, str) and len(value) > 1):
                            # Check if it's not a numeric string
                            is_numeric = False
                            try:
                                float(value)
                                is_numeric = True
                            except (ValueError, TypeError):
                                pass
                            
                            if not is_numeric:
                                if value not in self.string_literals:
                                    label = f".LC{self.string_counter}"
                                    self.string_literals[value] = label
                                    self.string_counter += 1
        
        # Emit string literal data section
        if self.string_literals:
            self.emit(".section .rodata")
            for string_value, label in self.string_literals.items():
                # Escape the string for assembly
                escaped = string_value.replace('\\', '\\\\').replace('\n', '\\n').replace('\t', '\\t').replace('\r', '\\r').replace('"', '\\"').replace('\0', '\\0')
                self.emit(f"{label}:")
                self.emit(f'  .string "{escaped}"')
            self.emit("")
            self.emit(".text")
            self.emit("")
        
        # Generate code for each function
        for func in mir_functions:
            self.generate_function(func)
        
        return "\n".join(self.output)
    
    def generate_function(self, func):
        """Generate assembly for a MIR function."""
        self.current_function = func
        self.temp_to_reg = {}
        self.var_to_stack = {}
        self.stack_offset = 0
        self.max_stack_offset = 0
        self.temp_counter = 0
        self.reg_allocator.reset()
        
        # Map block labels
        entry_block_label = func.entry_block.label if func.entry_block else "entry"
        label_counter = 0
        for block in func.blocks:
            if block.label != entry_block_label:
                asm_label = f".L{func.name}_{label_counter}"
                label_counter += 1
                self.label_map[block.label] = asm_label
        
        # Function prologue
        self.emit(f".globl {func.name}")
        self.emit(f".type {func.name}, @function")
        self.emit(f"{func.name}:")
        self.emit("  pushq %rbp")
        self.emit("  movq %rsp, %rbp")
        
        # Calculate stack space needed for local variables
        self.collect_variables(func)
        
        # Allocate stack space for local variables
        if self.max_stack_offset > 0:
            # Align stack to 16 bytes
            stack_size = ((self.max_stack_offset + 15) // 16) * 16
            self.emit(f"  subq ${stack_size}, %rsp")
        
        # Store function parameters to stack (System V ABI: rdi, rsi, rdx, rcx, r8, r9)
        param_regs = ['%rdi', '%rsi', '%rdx', '%rcx', '%r8', '%r9']
        for i, param_name in enumerate(func.parameters):
            if param_name in self.var_to_stack:
                stack_offset = self.var_to_stack[param_name]
                if i < len(param_regs):
                    # Parameter in register
                    self.emit(f"  movq {param_regs[i]}, -{stack_offset}(%rbp)")
                else:
                    # Parameter on stack (16 bytes above saved rbp for first stack param)
                    # Function parameters are at 16(%rbp), 24(%rbp), etc.
                    param_stack_offset = 16 + (i - 6) * 8
                    self.emit(f"  movq {param_stack_offset}(%rbp), %rax")
                    self.emit(f"  movq %rax, -{stack_offset}(%rbp)")
        
        # Track if we've emitted a return
        self.has_return = False
        
        # Generate code for each basic block
        # We need to generate all blocks, even if some have returns,
        # because other blocks might be reachable via different paths
        for block in func.blocks:
            self.generate_block(block)
        
        # Function epilogue (if no explicit return was generated)
        if not self.has_return:
            self.emit("  movq $0, %rax")  # Default return 0
            self.emit("  leave")
            self.emit("  ret")
        
        self.emit("")
        self.emit(f".size {func.name}, .-{func.name}")
        self.emit("")
    
    def collect_variables(self, func):
        """Collect all variables that need stack allocation."""
        for block in func.blocks:
            for instr in block.instructions:
                if instr.op == Op.LOAD:
                    var_name = instr.operands[0]
                    if var_name not in self.var_to_stack:
                        self.var_to_stack[var_name] = self.stack_offset + 8
                        self.stack_offset += 8
                        self.max_stack_offset = max(self.max_stack_offset, self.stack_offset)
                elif instr.op == Op.STORE:
                    var_name = instr.operands[0]
                    if var_name not in self.var_to_stack:
                        self.var_to_stack[var_name] = self.stack_offset + 8
                        self.stack_offset += 8
                        self.max_stack_offset = max(self.max_stack_offset, self.stack_offset)
    
    def generate_block(self, block):
        """Generate assembly for a basic block."""
        # Emit block label (entry block doesn't need a label)
        asm_label = self.label_map.get(block.label)
        if asm_label is not None:
            self.emit(f"{asm_label}:")
        
        # Process instructions
        self.pending_params = []
        for instr in block.instructions:
            self.generate_instruction(instr)
            # Stop processing after return
            if instr.op in (Op.RETURN, Op.RETVAL):
                break
    
    def generate_instruction(self, instr):
        """Generate assembly for a single instruction."""
        op = instr.op
        operands = instr.operands
        result = instr.result
        
        if op == Op.CONST:
            value = operands[0]
            # Check if it's a string
            is_string = False
            if value in self.string_literals:
                try:
                    float(value)
                    is_string = False
                except (ValueError, TypeError):
                    is_string = True
            
            if hasattr(instr, 'operand_types') and instr.operand_types and len(instr.operand_types) > 0:
                type_str = str(instr.operand_types[0]).lower()
                if type_str == "string":
                    is_string = True
            
            if result:
                if is_string:
                    # String literal: load address
                    label = self.string_literals[value]
                    reg = self.reg_allocator.allocate()
                    self.emit(f"  leaq {label}(%rip), {reg}")
                    self.temp_to_reg[result] = reg
                else:
                    # Numeric constant
                    num_value = self.get_numeric_value(value)
                    reg = self.reg_allocator.allocate()
                    if isinstance(num_value, float):
                        # For floats, we'll use integer representation for now
                        # In a full implementation, we'd use xmm registers
                        int_val = int(num_value)
                        self.emit(f"  movq ${int_val}, {reg}")
                    else:
                        self.emit(f"  movq ${num_value}, {reg}")
                    self.temp_to_reg[result] = reg
        
        elif op == Op.LOAD:
            var_name = operands[0]
            if result:
                stack_offset = self.var_to_stack.get(var_name, 0)
                if stack_offset == 0:
                    # Variable not found, assume it's a parameter
                    # Try to find it in parameter list
                    if var_name in self.current_function.parameters:
                        param_idx = self.current_function.parameters.index(var_name)
                        if param_idx < 6:
                            reg = self.reg_allocator.allocate()
                            param_regs = ['%rdi', '%rsi', '%rdx', '%rcx', '%r8', '%r9']
                            self.emit(f"  movq {param_regs[param_idx]}, {reg}")
                            self.temp_to_reg[result] = reg
                        else:
                            # Parameter on stack
                            param_stack_offset = 16 + (param_idx - 6) * 8
                            reg = self.reg_allocator.allocate()
                            self.emit(f"  movq {param_stack_offset}(%rbp), {reg}")
                            self.temp_to_reg[result] = reg
                    else:
                        # Unknown variable, use 0
                        reg = self.reg_allocator.allocate()
                        self.emit(f"  movq $0, {reg}")
                        self.temp_to_reg[result] = reg
                else:
                    reg = self.reg_allocator.allocate()
                    self.emit(f"  movq -{stack_offset}(%rbp), {reg}")
                    self.temp_to_reg[result] = reg
        
        elif op == Op.STORE:
            var_name = operands[0]
            value_temp = operands[1]
            stack_offset = self.var_to_stack.get(var_name, 0)
            if stack_offset == 0:
                # Variable not allocated, skip
                pass
            else:
                value_reg = self.get_temp_reg(value_temp)
                self.emit(f"  movq {value_reg}, -{stack_offset}(%rbp)")
        
        elif op == Op.ADD:
            if result:
                left_reg = self.get_temp_reg(operands[0])
                right_reg = self.get_temp_reg(operands[1])
                result_reg = self.reg_allocator.allocate()
                self.emit(f"  movq {left_reg}, {result_reg}")
                self.emit(f"  addq {right_reg}, {result_reg}")
                self.temp_to_reg[result] = result_reg
        
        elif op == Op.SUB:
            if result:
                left_reg = self.get_temp_reg(operands[0])
                right_reg = self.get_temp_reg(operands[1])
                result_reg = self.reg_allocator.allocate()
                self.emit(f"  movq {left_reg}, {result_reg}")
                self.emit(f"  subq {right_reg}, {result_reg}")
                self.temp_to_reg[result] = result_reg
        
        elif op == Op.MUL:
            if result:
                left_reg = self.get_temp_reg(operands[0])
                right_reg = self.get_temp_reg(operands[1])
                result_reg = self.reg_allocator.allocate()
                self.emit(f"  movq {left_reg}, %rax")
                self.emit(f"  imulq {right_reg}")
                self.emit(f"  movq %rax, {result_reg}")
                self.temp_to_reg[result] = result_reg
        
        elif op == Op.DIV:
            if result:
                left_reg = self.get_temp_reg(operands[0])
                right_reg = self.get_temp_reg(operands[1])
                result_reg = self.reg_allocator.allocate()
                # x86-64 signed division: dividend in rax, divisor in register
                self.emit(f"  movq {left_reg}, %rax")
                self.emit(f"  cqto")  # Sign extend rax to rdx:rax
                self.emit(f"  idivq {right_reg}")
                self.emit(f"  movq %rax, {result_reg}")
                self.temp_to_reg[result] = result_reg
        
        elif op == Op.MOD:
            if result:
                left_reg = self.get_temp_reg(operands[0])
                right_reg = self.get_temp_reg(operands[1])
                result_reg = self.reg_allocator.allocate()
                self.emit(f"  movq {left_reg}, %rax")
                self.emit(f"  cqto")
                self.emit(f"  idivq {right_reg}")
                self.emit(f"  movq %rdx, {result_reg}")  # Remainder in rdx
                self.temp_to_reg[result] = result_reg
        
        elif op == Op.SHL:
            # Left shift: shlq %cl, %reg (or shlq $imm, %reg)
            if result:
                left_reg = self.get_temp_reg(operands[0])
                right_reg = self.get_temp_reg(operands[1])
                result_reg = self.reg_allocator.allocate()
                self.emit(f"  movq {left_reg}, {result_reg}")
                # Check if right operand is a constant
                if isinstance(operands[1], str) and operands[1].isdigit():
                    # Immediate shift
                    self.emit(f"  shlq ${operands[1]}, {result_reg}")
                else:
                    # Shift by register (must be %cl for x86-64)
                    # Move right operand to %cl
                    self.emit(f"  movq {right_reg}, %rcx")
                    self.emit(f"  shlq %cl, {result_reg}")
                self.temp_to_reg[result] = result_reg
        
        elif op == Op.SHR:
            # Right shift (arithmetic): sarq %cl, %reg (or sarq $imm, %reg)
            if result:
                left_reg = self.get_temp_reg(operands[0])
                right_reg = self.get_temp_reg(operands[1])
                result_reg = self.reg_allocator.allocate()
                self.emit(f"  movq {left_reg}, {result_reg}")
                # Check if right operand is a constant
                if isinstance(operands[1], str) and operands[1].isdigit():
                    # Immediate shift
                    self.emit(f"  sarq ${operands[1]}, {result_reg}")
                else:
                    # Shift by register (must be %cl for x86-64)
                    # Move right operand to %cl
                    self.emit(f"  movq {right_reg}, %rcx")
                    self.emit(f"  sarq %cl, {result_reg}")
                self.temp_to_reg[result] = result_reg
        
        elif op == Op.EQ:
            if result:
                left_reg = self.get_temp_reg(operands[0])
                right_reg = self.get_temp_reg(operands[1])
                result_reg = self.reg_allocator.allocate()
                self.emit(f"  cmpq {right_reg}, {left_reg}")
                self.emit(f"  sete %al")
                self.emit(f"  movzbq %al, {result_reg}")
                self.temp_to_reg[result] = result_reg
        
        elif op == Op.NE:
            if result:
                left_reg = self.get_temp_reg(operands[0])
                right_reg = self.get_temp_reg(operands[1])
                result_reg = self.reg_allocator.allocate()
                self.emit(f"  cmpq {right_reg}, {left_reg}")
                self.emit(f"  setne %al")
                self.emit(f"  movzbq %al, {result_reg}")
                self.temp_to_reg[result] = result_reg
        
        elif op == Op.LT:
            if result:
                left_reg = self.get_temp_reg(operands[0])
                right_reg = self.get_temp_reg(operands[1])
                result_reg = self.reg_allocator.allocate()
                self.emit(f"  cmpq {right_reg}, {left_reg}")
                self.emit(f"  setl %al")
                self.emit(f"  movzbq %al, {result_reg}")
                self.temp_to_reg[result] = result_reg
        
        elif op == Op.LE:
            if result:
                left_reg = self.get_temp_reg(operands[0])
                right_reg = self.get_temp_reg(operands[1])
                result_reg = self.reg_allocator.allocate()
                self.emit(f"  cmpq {right_reg}, {left_reg}")
                self.emit(f"  setle %al")
                self.emit(f"  movzbq %al, {result_reg}")
                self.temp_to_reg[result] = result_reg
        
        elif op == Op.GT:
            if result:
                left_reg = self.get_temp_reg(operands[0])
                right_reg = self.get_temp_reg(operands[1])
                result_reg = self.reg_allocator.allocate()
                self.emit(f"  cmpq {right_reg}, {left_reg}")
                self.emit(f"  setg %al")
                self.emit(f"  movzbq %al, {result_reg}")
                self.temp_to_reg[result] = result_reg
        
        elif op == Op.GE:
            if result:
                left_reg = self.get_temp_reg(operands[0])
                right_reg = self.get_temp_reg(operands[1])
                result_reg = self.reg_allocator.allocate()
                self.emit(f"  cmpq {right_reg}, {left_reg}")
                self.emit(f"  setge %al")
                self.emit(f"  movzbq %al, {result_reg}")
                self.temp_to_reg[result] = result_reg
        
        elif op == Op.BRANCH:
            cond_temp = operands[0]
            true_label = self.label_map.get(operands[1], operands[1])
            false_label = self.label_map.get(operands[2], operands[2])
            cond_reg = self.get_temp_reg(cond_temp)
            self.emit(f"  cmpq $0, {cond_reg}")
            self.emit(f"  jne {true_label}")
            self.emit(f"  jmp {false_label}")
        
        elif op == Op.JUMP:
            target_label = self.label_map.get(operands[0], operands[0])
            self.emit(f"  jmp {target_label}")
        
        elif op == Op.PARAM:
            # Collect parameters for function call
            param_temp = operands[0]
            self.pending_params.append(param_temp)
        
        elif op == Op.CALL:
            func_name = operands[0]
            # Handle print function specially
            if func_name == "print":
                self.handle_print_call()
            else:
                # Regular function call
                # System V ABI: first 6 args in rdi, rsi, rdx, rcx, r8, r9
                param_regs = ['%rdi', '%rsi', '%rdx', '%rcx', '%r8', '%r9']
                for i, param_temp in enumerate(self.pending_params):
                    param_reg = self.get_temp_reg(param_temp)
                    if i < len(param_regs):
                        self.emit(f"  movq {param_reg}, {param_regs[i]}")
                    else:
                        # Push remaining parameters to stack (right to left)
                        self.emit(f"  pushq {param_reg}")
                
                # Align stack to 16 bytes before call
                num_stack_params = max(0, len(self.pending_params) - 6)
                if num_stack_params % 2 == 1:
                    self.emit("  subq $8, %rsp")  # Align stack
                
                self.emit(f"  call {func_name}")
                
                # Restore stack
                if num_stack_params > 0:
                    stack_restore = num_stack_params * 8
                    if num_stack_params % 2 == 1:
                        stack_restore += 8
                    self.emit(f"  addq ${stack_restore}, %rsp")
                
                if result:
                    # Return value in rax
                    result_reg = self.reg_allocator.allocate()
                    self.emit(f"  movq %rax, {result_reg}")
                    self.temp_to_reg[result] = result_reg
            
            self.pending_params = []
        
        elif op == Op.RETURN:
            self.emit("  movq $0, %rax")
            self.emit("  leave")
            self.emit("  ret")
            self.has_return = True
        
        elif op == Op.RETVAL:
            value_temp = operands[0]
            value_reg = self.get_temp_reg(value_temp)
            self.emit(f"  movq {value_reg}, %rax")
            self.emit("  leave")
            self.emit("  ret")
            self.has_return = True
    
    def handle_print_call(self):
        """Handle print function call - use printf from libc."""
        # For print, we need to handle multiple arguments with format string
        # This is a simplified version - in practice, we'd need proper format string generation
        
        # Save caller-saved registers
        self.emit("  pushq %rax")
        self.emit("  pushq %rcx")
        self.emit("  pushq %rdx")
        self.emit("  pushq %rsi")
        self.emit("  pushq %rdi")
        self.emit("  pushq %r8")
        self.emit("  pushq %r9")
        self.emit("  pushq %r10")
        self.emit("  pushq %r11")
        
        # Align stack to 16 bytes
        self.emit("  subq $8, %rsp")
        
        # For now, just print each argument (simplified)
        # In a full implementation, we'd generate proper format strings
        for i, param_temp in enumerate(self.pending_params):
            param_reg = self.get_temp_reg(param_temp)
            if i == 0:
                # First argument (format string or value)
                self.emit(f"  movq {param_reg}, %rdi")
            elif i == 1:
                self.emit(f"  movq {param_reg}, %rsi")
            elif i == 2:
                self.emit(f"  movq {param_reg}, %rdx")
            elif i == 3:
                self.emit(f"  movq {param_reg}, %rcx")
            elif i == 4:
                self.emit(f"  movq {param_reg}, %r8")
            elif i == 5:
                self.emit(f"  movq {param_reg}, %r9")
            else:
                self.emit(f"  pushq {param_reg}")
        
        # Call printf (we'll need to link with libc)
        # For now, use a simple approach - in practice, we'd need proper format strings
        self.emit("  call printf")
        
        # Restore stack
        num_stack_params = max(0, len(self.pending_params) - 6)
        if num_stack_params > 0:
            self.emit(f"  addq ${num_stack_params * 8}, %rsp")
        self.emit("  addq $8, %rsp")  # Remove alignment
        
        # Restore registers
        self.emit("  popq %r11")
        self.emit("  popq %r10")
        self.emit("  popq %r9")
        self.emit("  popq %r8")
        self.emit("  popq %rdi")
        self.emit("  popq %rsi")
        self.emit("  popq %rdx")
        self.emit("  popq %rcx")
        self.emit("  popq %rax")
    
    def get_temp_reg(self, temp):
        """Get register for a temporary, allocating if necessary."""
        if temp in self.temp_to_reg:
            return self.temp_to_reg[temp]
        else:
            # Temporary not found, assume it's a constant or use a default
            reg = self.reg_allocator.allocate()
            self.temp_to_reg[temp] = reg
            return reg
    
    def get_numeric_value(self, value):
        """Convert a value to a numeric type."""
        if isinstance(value, (int, float)):
            return value
        elif isinstance(value, str):
            # Try to parse as number
            try:
                if '.' in value:
                    return float(value)
                else:
                    return int(value)
            except ValueError:
                # If it's a single character, return its ASCII value
                if len(value) == 1:
                    return ord(value)
                return 0
        return 0


class RegisterAllocator:
    """Simple register allocator for x86-64."""
    
    def __init__(self):
        self.available_regs = ['%r10', '%r11', '%r12', '%r13', '%r14', '%r15', '%rbx']
        self.used_regs = []
        self.reg_map = {}
    
    def allocate(self):
        """Allocate a register."""
        if self.available_regs:
            reg = self.available_regs.pop(0)
            self.used_regs.append(reg)
            return reg
        else:
            # No more registers, reuse one (simple approach)
            if self.used_regs:
                return self.used_regs[0]
            return '%rax'  # Fallback
    
    def reset(self):
        """Reset allocator for a new function."""
        self.available_regs = ['%r10', '%r11', '%r12', '%r13', '%r14', '%r15', '%rbx']
        self.used_regs = []
        self.reg_map = {}

