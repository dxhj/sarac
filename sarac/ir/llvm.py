"""
LLVM IR code generator for the Sarac compiler.

Converts MIR (Mid-level Intermediate Representation) to LLVM IR.
"""

from sarac.ir.mir import MIRFunction, BasicBlock, Instruction, Op


class LLVMGenerator:
    """Converts MIR to LLVM IR."""
    
    def __init__(self):
        self.output = []  # List of output lines
        self.temp_to_llvm = {}  # Map MIR temps to LLVM values
        self.var_to_llvm = {}  # Map variable names to LLVM alloca instructions
        self.label_map = {}  # Map MIR block labels to LLVM labels
        self.llvm_temp_counter = 0  # Counter for LLVM temporaries
        self.current_function = None
        self.pending_params = []  # Parameters collected before a CALL
        self.alloca_instructions = []  # Alloca instructions to emit at function start
    
    def type_to_llvm(self, sarac_type):
        """Convert Sarac type to LLVM type."""
        if sarac_type is None:
            return "void"
        type_str = str(sarac_type).lower()
        if type_str == "int":
            return "i32"
        elif type_str == "char":
            return "i8"
        elif type_str == "void":
            return "void"
        else:
            return "i32"  # Default to i32
    
    def new_llvm_temp(self):
        """Generate a new LLVM temporary variable name."""
        temp = f"%{self.llvm_temp_counter}"
        self.llvm_temp_counter += 1
        return temp
    
    def emit(self, line):
        """Emit a line of LLVM IR."""
        self.output.append(line)
    
    def generate(self, mir_functions):
        """Generate LLVM IR for a list of MIR functions."""
        self.output = []
        
        # Generate all function declarations first (for forward references)
        for func in mir_functions:
            self.emit_function_declaration(func)
        if mir_functions:
            self.emit("")  # Blank line between declarations and definitions
        
        # Generate function definitions
        for func in mir_functions:
            self.generate_function(func)
        
        return "\n".join(self.output)
    
    def emit_function_declaration(self, func):
        """Emit function declaration (for forward references)."""
        return_type = self.type_to_llvm(func.return_type)
        if func.parameter_types:
            param_types = [self.type_to_llvm(pt) for pt in func.parameter_types]
        else:
            param_types = [self.type_to_llvm("int") for _ in func.parameters]
        param_str = ", ".join(param_types) if param_types else "void"
        self.emit(f"declare {return_type} @{func.name}({param_str})")
    
    def generate_function(self, func):
        """Generate LLVM IR for a single MIR function."""
        self.current_function = func
        self.temp_to_llvm = {}
        self.var_to_llvm = {}
        self.label_map = {}
        self.llvm_temp_counter = 0
        self.alloca_instructions = []
        
        # Function signature
        return_type = self.type_to_llvm(func.return_type)
        if func.parameter_types:
            param_types = [self.type_to_llvm(pt) for pt in func.parameter_types]
        else:
            param_types = [self.type_to_llvm("int") for _ in func.parameters]
        
        if func.parameters:
            param_str = ", ".join([f"{pt} %{p}" for pt, p in zip(param_types, func.parameters)])
        else:
            param_str = ""
        
        self.emit(f"define {return_type} @{func.name}({param_str}) {{")
        
        # Map entry block
        if func.entry_block:
            self.label_map[func.entry_block.label] = "entry"
        
        # Map all other blocks
        for block in func.blocks:
            if block != func.entry_block:
                llvm_label = f"label{len(self.label_map)}"
                self.label_map[block.label] = llvm_label
        
        # First pass: collect all variables that need allocation
        self.collect_variables(func)
        
        # Emit alloca instructions at the start of entry block
        if self.alloca_instructions:
            for alloca_line in self.alloca_instructions:
                self.emit(f"  {alloca_line}")
        
        # Store function parameters into allocas
        for i, param_name in enumerate(func.parameters):
            if param_name not in self.var_to_llvm:
                continue
            param_type = param_types[i] if i < len(param_types) else "i32"
            alloca = self.var_to_llvm[param_name]
            param_temp = f"%{param_name}"
            self.emit(f"  store {param_type} {param_temp}, {param_type}* {alloca}")
        
        # Generate code for each basic block
        for block in func.blocks:
            self.generate_block(block)
        
        self.emit("}")
        self.emit("")  # Blank line between functions
    
    def collect_variables(self, func):
        """First pass: collect all variables that need allocation."""
        for block in func.blocks:
            for instr in block.instructions:
                if instr.op == Op.LOAD:
                    var_name = instr.operands[0]
                    if var_name not in self.var_to_llvm:
                        llvm_type = "i32"  # TODO: get actual type
                        alloca_temp = self.new_llvm_temp()
                        self.var_to_llvm[var_name] = alloca_temp
                        self.alloca_instructions.append(f"{alloca_temp} = alloca {llvm_type}")
                elif instr.op == Op.STORE:
                    var_name = instr.operands[0]
                    if var_name not in self.var_to_llvm:
                        llvm_type = "i32"  # TODO: get actual type
                        alloca_temp = self.new_llvm_temp()
                        self.var_to_llvm[var_name] = alloca_temp
                        self.alloca_instructions.append(f"{alloca_temp} = alloca {llvm_type}")
        
        # Also allocate for function parameters
        if func.parameter_types:
            param_types = [self.type_to_llvm(pt) for pt in func.parameter_types]
        else:
            param_types = [self.type_to_llvm("int") for _ in func.parameters]
        
        for i, param_name in enumerate(func.parameters):
            if param_name not in self.var_to_llvm:
                param_type = param_types[i] if i < len(param_types) else "i32"
                alloca_temp = self.new_llvm_temp()
                self.var_to_llvm[param_name] = alloca_temp
                self.alloca_instructions.append(f"{alloca_temp} = alloca {param_type}")
    
    def generate_block(self, block):
        """Generate LLVM IR for a basic block."""
        # Emit block label
        llvm_label = self.label_map.get(block.label, block.label)
        if llvm_label != "entry" or block != self.current_function.entry_block:
            self.emit(f"{llvm_label}:")
        
        # Process instructions
        self.pending_params = []  # Reset for each block
        for instr in block.instructions:
            self.generate_instruction(instr)
    
    def generate_instruction(self, instr):
        """Generate LLVM IR for a single instruction."""
        op = instr.op
        operands = instr.operands
        result = instr.result
        
        if op == Op.CONST:
            # Constant: store the constant value directly in the mapping
            # We don't need to emit an instruction - we'll use the constant directly
            value = operands[0]
            llvm_value = self.get_llvm_value(value)
            # Map the MIR temporary to the constant value directly
            if result:
                self.temp_to_llvm[result] = llvm_value
        
        elif op == Op.LOAD:
            # Load variable: %t = load i32, i32* %var
            var_name = operands[0]
            llvm_type = "i32"  # TODO: get actual type
            llvm_var = self.var_to_llvm.get(var_name)
            if not llvm_var:
                # Should have been collected in first pass, but handle gracefully
                llvm_var = self.new_llvm_temp()
                self.var_to_llvm[var_name] = llvm_var
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = load {llvm_type}, {llvm_type}* {llvm_var}")
            if result:
                self.temp_to_llvm[result] = llvm_temp
        
        elif op == Op.STORE:
            # Store: store i32 %value, i32* %var
            var_name = operands[0]
            value_temp = operands[1]
            llvm_type = "i32"  # TODO: get actual type
            llvm_var = self.var_to_llvm.get(var_name)
            if not llvm_var:
                # Should have been collected in first pass, but handle gracefully
                llvm_var = self.new_llvm_temp()
                self.var_to_llvm[var_name] = llvm_var
            llvm_value = self.get_llvm_value(value_temp)
            self.emit(f"  store {llvm_type} {llvm_value}, {llvm_type}* {llvm_var}")
        
        elif op == Op.ADD:
            # Add: %t = add i32 %a, %b
            a = self.get_llvm_value(operands[0])
            b = self.get_llvm_value(operands[1])
            llvm_type = "i32"
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = add {llvm_type} {a}, {b}")
            if result:
                self.temp_to_llvm[result] = llvm_temp
        
        elif op == Op.SUB:
            # Subtract: %t = sub i32 %a, %b
            a = self.get_llvm_value(operands[0])
            b = self.get_llvm_value(operands[1])
            llvm_type = "i32"
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = sub {llvm_type} {a}, {b}")
            if result:
                self.temp_to_llvm[result] = llvm_temp
        
        elif op == Op.MUL:
            # Multiply: %t = mul i32 %a, %b
            a = self.get_llvm_value(operands[0])
            b = self.get_llvm_value(operands[1])
            llvm_type = "i32"
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = mul {llvm_type} {a}, {b}")
            if result:
                self.temp_to_llvm[result] = llvm_temp
        
        elif op == Op.DIV:
            # Divide: %t = sdiv i32 %a, %b
            a = self.get_llvm_value(operands[0])
            b = self.get_llvm_value(operands[1])
            llvm_type = "i32"
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = sdiv {llvm_type} {a}, {b}")
            if result:
                self.temp_to_llvm[result] = llvm_temp
        
        elif op == Op.MOD:
            # Modulo: %t = srem i32 %a, %b
            a = self.get_llvm_value(operands[0])
            b = self.get_llvm_value(operands[1])
            llvm_type = "i32"
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = srem {llvm_type} {a}, {b}")
            if result:
                self.temp_to_llvm[result] = llvm_temp
        
        elif op == Op.EQ:
            # Equal: %t = icmp eq i32 %a, %b
            a = self.get_llvm_value(operands[0])
            b = self.get_llvm_value(operands[1])
            llvm_type = "i32"
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = icmp eq {llvm_type} {a}, {b}")
            if result:
                self.temp_to_llvm[result] = llvm_temp
        
        elif op == Op.NE:
            # Not equal: %t = icmp ne i32 %a, %b
            a = self.get_llvm_value(operands[0])
            b = self.get_llvm_value(operands[1])
            llvm_type = "i32"
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = icmp ne {llvm_type} {a}, {b}")
            if result:
                self.temp_to_llvm[result] = llvm_temp
        
        elif op == Op.LT:
            # Less than: %t = icmp slt i32 %a, %b
            a = self.get_llvm_value(operands[0])
            b = self.get_llvm_value(operands[1])
            llvm_type = "i32"
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = icmp slt {llvm_type} {a}, {b}")
            if result:
                self.temp_to_llvm[result] = llvm_temp
        
        elif op == Op.LE:
            # Less or equal: %t = icmp sle i32 %a, %b
            a = self.get_llvm_value(operands[0])
            b = self.get_llvm_value(operands[1])
            llvm_type = "i32"
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = icmp sle {llvm_type} {a}, {b}")
            if result:
                self.temp_to_llvm[result] = llvm_temp
        
        elif op == Op.GT:
            # Greater than: %t = icmp sgt i32 %a, %b
            a = self.get_llvm_value(operands[0])
            b = self.get_llvm_value(operands[1])
            llvm_type = "i32"
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = icmp sgt {llvm_type} {a}, {b}")
            if result:
                self.temp_to_llvm[result] = llvm_temp
        
        elif op == Op.GE:
            # Greater or equal: %t = icmp sge i32 %a, %b
            a = self.get_llvm_value(operands[0])
            b = self.get_llvm_value(operands[1])
            llvm_type = "i32"
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = icmp sge {llvm_type} {a}, {b}")
            if result:
                self.temp_to_llvm[result] = llvm_temp
        
        elif op == Op.AND:
            # Logical AND: %t = and i1 %a, %b
            a = self.get_llvm_value(operands[0])
            b = self.get_llvm_value(operands[1])
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = and i1 {a}, {b}")
            if result:
                self.temp_to_llvm[result] = llvm_temp
        
        elif op == Op.OR:
            # Logical OR: %t = or i1 %a, %b
            a = self.get_llvm_value(operands[0])
            b = self.get_llvm_value(operands[1])
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = or i1 {a}, {b}")
            if result:
                self.temp_to_llvm[result] = llvm_temp
        
        elif op == Op.NOT:
            # Logical NOT: %t = xor i1 %a, 1
            a = self.get_llvm_value(operands[0])
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = xor i1 {a}, 1")
            if result:
                self.temp_to_llvm[result] = llvm_temp
        
        elif op == Op.NEG:
            # Negate: %t = sub i32 0, %a
            a = self.get_llvm_value(operands[0])
            llvm_type = "i32"
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = sub {llvm_type} 0, {a}")
            if result:
                self.temp_to_llvm[result] = llvm_temp
        
        elif op == Op.BRANCH:
            # Conditional branch: br i1 %cond, label %then, label %else
            cond = self.get_llvm_value(operands[0])
            then_label = self.label_map.get(operands[1], operands[1])
            else_label = self.label_map.get(operands[2], operands[2])
            self.emit(f"  br i1 {cond}, label %{then_label}, label %{else_label}")
        
        elif op == Op.JUMP:
            # Unconditional jump: br label %target
            target_label = self.label_map.get(operands[0], operands[0])
            self.emit(f"  br label %{target_label}")
        
        elif op == Op.RETURN:
            # Return void: ret void
            self.emit("  ret void")
        
        elif op == Op.RETVAL:
            # Return value: ret i32 %value
            value = self.get_llvm_value(operands[0])
            return_type = self.type_to_llvm(self.current_function.return_type)
            self.emit(f"  ret {return_type} {value}")
        
        elif op == Op.PARAM:
            # Parameter passing - collect for next CALL
            param_value = self.get_llvm_value(operands[0])
            self.pending_params.append(param_value)
        
        elif op == Op.CALL:
            # Function call: %t = call i32 @func(i32 %arg1, i32 %arg2, ...)
            func_name = operands[0]
            return_type = "i32"  # TODO: get actual return type from function signature
            
            # Use collected parameters
            params = self.pending_params
            self.pending_params = []  # Reset for next call
            
            # Build parameter list
            if params:
                param_str = ", ".join([f"i32 {p}" for p in params])
            else:
                param_str = ""
            
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = call {return_type} @{func_name}({param_str})")
            if result:
                self.temp_to_llvm[result] = llvm_temp
    
    def get_llvm_value(self, operand):
        """Get LLVM representation of an operand (temp, constant, or variable)."""
        # Check if it's a temporary
        if operand in self.temp_to_llvm:
            return self.temp_to_llvm[operand]
        
        # Check if it's a character literal
        if isinstance(operand, str):
            # Check for character literal format: 'x' (with single quotes)
            if len(operand) >= 3 and operand[0] == "'" and operand[-1] == "'":
                # Extract the character (handle escape sequences)
                char_str = operand[1:-1]
                if len(char_str) == 1:
                    return str(ord(char_str))
                elif len(char_str) == 2 and char_str[0] == '\\':
                    # Handle escape sequences like '\n', '\t', etc.
                    escape_map = {'n': '\n', 't': '\t', 'r': '\r', '\\': '\\', "'": "'", '"': '"'}
                    char = escape_map.get(char_str[1], char_str[1])
                    return str(ord(char))
            # Check if it's a single character (character literal value from Constant node)
            elif len(operand) == 1:
                # This is a character literal value (like 'a' stored as the string 'a')
                return str(ord(operand))
            # Try to parse as integer
            try:
                int_val = int(operand)
                return str(int_val)
            except ValueError:
                pass
        
        # Check if it's an integer
        if isinstance(operand, int):
            return str(operand)
        
        # Otherwise, treat as constant (might be a variable name or other)
        return str(operand)

