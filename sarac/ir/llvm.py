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
        self.llvm_temp_counter = 1  # Counter for LLVM temporaries (start at 1, not 0)
        self.current_function = None
        self.pending_params = []  # Parameters collected before a CALL
        self.alloca_instructions = []  # Alloca instructions to emit at function start
        self.i1_temporaries = set()  # Track which temporaries are i1 (from comparisons)
        self.string_literals = {}  # Map string values to global constant names
        self.string_counter = 0  # Counter for string literal names
    
    def type_to_llvm(self, sarac_type):
        """Convert Sarac type to LLVM type."""
        if sarac_type is None:
            return "void"
        type_str = str(sarac_type).lower()
        if type_str == "int":
            return "i32"
        elif type_str == "char":
            return "i8"
        elif type_str == "string":
            return "i8*"
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
        self.string_literals = {}
        self.string_counter = 0
        
        # First pass: collect all string literals
        for func in mir_functions:
            for block in func.blocks:
                for instr in block.instructions:
                    if instr.op == Op.CONST and instr.operands:
                        value = instr.operands[0]
                        # Check if it's a string type
                        is_string_type = False
                        if instr.operand_types and len(instr.operand_types) > 0:
                            type_str = str(instr.operand_types[0]).lower()
                            is_string_type = (type_str == "string")
                        
                        # If it's a string type, or if it's a multi-character string that's not numeric
                        if is_string_type or (isinstance(value, str) and len(value) > 1):
                            # Check if it's not a numeric string
                            try:
                                int(value)
                            except ValueError:
                                # Not a number, it's a string literal
                                if value not in self.string_literals:
                                    global_name = f"@.str{self.string_counter}"
                                    self.string_literals[value] = global_name
                                    self.string_counter += 1
        
        # Emit string literal global constants
        for string_value, global_name in self.string_literals.items():
            # Escape the string for LLVM IR
            escaped = string_value.replace('\\', '\\5C').replace('\n', '\\0A').replace('\t', '\\09').replace('\r', '\\0D').replace('"', '\\22').replace('\0', '\\00')
            # Create null-terminated string
            self.emit(f"{global_name} = private unnamed_addr constant [{len(string_value) + 1} x i8] c\"{escaped}\\00\"")
        
        if self.string_literals:
            self.emit("")  # Blank line after string literals
        
        # Track which functions are defined
        defined_functions = {func.name for func in mir_functions}
        
        # Collect all function calls to find which functions need declarations
        called_functions = set()
        for func in mir_functions:
            for block in func.blocks:
                for instr in block.instructions:
                    if instr.op == Op.CALL:
                        called_functions.add(instr.operands[0])
        
        # Only declare functions that are called but not defined
        functions_to_declare = called_functions - defined_functions
        if functions_to_declare:
            # We need to declare external functions, but we don't have their signatures
            # For now, we'll skip declarations since we don't have enough info
            # In a real compiler, you'd look up function signatures from a symbol table
            pass
        
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
        # For void functions with no parameters, use empty parentheses
        if param_types:
            param_str = ", ".join(param_types)
        else:
            param_str = ""
        self.emit(f"declare {return_type} @{func.name}({param_str})")
    
    def generate_function(self, func):
        """Generate LLVM IR for a single MIR function."""
        self.current_function = func
        self.temp_to_llvm = {}
        self.var_to_llvm = {}
        self.label_map = {}
        self.llvm_temp_counter = 1  # Start at 1 for LLVM IR numbering
        self.alloca_instructions = []
        self.i1_temporaries = set()  # Track which temporaries are i1 (from comparisons)
        
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
        
        # Map entry block - entry block doesn't need a label in LLVM
        # The first block is typically the entry block
        entry_block_label = None
        if func.blocks:
            # First block is the entry block
            entry_block_label = func.blocks[0].label
            self.label_map[entry_block_label] = None  # Entry block has no label
        
        # Map all other blocks - use numeric labels
        label_counter = 0
        for block in func.blocks:
            if block.label != entry_block_label:
                llvm_label = f"bb{label_counter}"
                label_counter += 1
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
        # Emit block label (entry block doesn't need a label)
        # Entry block is mapped to None in label_map
        llvm_label = self.label_map.get(block.label)
        if llvm_label is not None:  # Only emit label for non-entry blocks
            self.emit(f"{llvm_label}:")
        
        # Process instructions
        self.pending_params = []  # Reset for each block
        for instr in block.instructions:
            self.generate_instruction(instr)
            # Stop processing after return (unreachable code)
            if instr.op in (Op.RETURN, Op.RETVAL):
                break
    
    def generate_instruction(self, instr):
        """Generate LLVM IR for a single instruction."""
        op = instr.op
        operands = instr.operands
        result = instr.result
        
        if op == Op.CONST:
            # Constant: if it has a result, we need to create a temporary for it
            # This ensures instruction numbering is sequential
            value = operands[0]
            # Check if it's a string literal
            is_string = value in self.string_literals
            
            # Also check type information if available
            if hasattr(instr, 'operand_types') and instr.operand_types and len(instr.operand_types) > 0:
                type_str = str(instr.operand_types[0]).lower()
                if type_str == "string":
                    is_string = True
            
            if result:
                if is_string:
                    # It's a string literal
                    global_name = self.string_literals[value]
                    llvm_temp = self.new_llvm_temp()
                    # Get pointer to string: getelementptr to get i8* from [N x i8]*
                    self.emit(f"  {llvm_temp} = getelementptr inbounds [{len(value) + 1} x i8], [{len(value) + 1} x i8]* {global_name}, i32 0, i32 0")
                    self.temp_to_llvm[result] = llvm_temp
                else:
                    # Number or character
                    llvm_value = self.get_llvm_value(value)
                    llvm_type = "i32"  # TODO: determine type from context (could be i8 for char)
                    llvm_temp = self.new_llvm_temp()
                    self.emit(f"  {llvm_temp} = add {llvm_type} 0, {llvm_value}")
                    self.temp_to_llvm[result] = llvm_temp
        
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
                self.i1_temporaries.add(llvm_temp)  # Comparison results are i1
        
        elif op == Op.NE:
            # Not equal: %t = icmp ne i32 %a, %b
            a = self.get_llvm_value(operands[0])
            b = self.get_llvm_value(operands[1])
            llvm_type = "i32"
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = icmp ne {llvm_type} {a}, {b}")
            if result:
                self.temp_to_llvm[result] = llvm_temp
                self.i1_temporaries.add(llvm_temp)  # Comparison results are i1
        
        elif op == Op.LT:
            # Less than: %t = icmp slt i32 %a, %b
            a = self.get_llvm_value(operands[0])
            b = self.get_llvm_value(operands[1])
            llvm_type = "i32"
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = icmp slt {llvm_type} {a}, {b}")
            if result:
                self.temp_to_llvm[result] = llvm_temp
                self.i1_temporaries.add(llvm_temp)  # Comparison results are i1
        
        elif op == Op.LE:
            # Less or equal: %t = icmp sle i32 %a, %b
            a = self.get_llvm_value(operands[0])
            b = self.get_llvm_value(operands[1])
            llvm_type = "i32"
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = icmp sle {llvm_type} {a}, {b}")
            if result:
                self.temp_to_llvm[result] = llvm_temp
                self.i1_temporaries.add(llvm_temp)  # Comparison results are i1
        
        elif op == Op.GT:
            # Greater than: %t = icmp sgt i32 %a, %b
            a = self.get_llvm_value(operands[0])
            b = self.get_llvm_value(operands[1])
            llvm_type = "i32"
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = icmp sgt {llvm_type} {a}, {b}")
            if result:
                self.temp_to_llvm[result] = llvm_temp
                self.i1_temporaries.add(llvm_temp)  # Comparison results are i1
        
        elif op == Op.GE:
            # Greater or equal: %t = icmp sge i32 %a, %b
            a = self.get_llvm_value(operands[0])
            b = self.get_llvm_value(operands[1])
            llvm_type = "i32"
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = icmp sge {llvm_type} {a}, {b}")
            if result:
                self.temp_to_llvm[result] = llvm_temp
                self.i1_temporaries.add(llvm_temp)  # Comparison results are i1
        
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
            # The condition must be an i1 temporary, not a constant or i32
            cond_value = self.get_llvm_value(operands[0])
            # Check if it's a constant (numeric string) or a temporary (starts with %)
            if cond_value.isdigit() or (len(cond_value) > 0 and cond_value[0] == '-' and cond_value[1:].isdigit()):
                # Constant - convert to i1 temporary
                cond_temp = self.new_llvm_temp()
                # Convert integer to i1: compare to 0
                self.emit(f"  {cond_temp} = icmp ne i32 {cond_value}, 0")
                cond = cond_temp
                self.i1_temporaries.add(cond_temp)
            elif cond_value.startswith('%'):
                # It's a temporary - check if it's already i1 (from a comparison)
                if cond_value in self.i1_temporaries:
                    # Already i1, use directly
                    cond = cond_value
                else:
                    # It's i32, convert to i1
                    cond_temp = self.new_llvm_temp()
                    self.emit(f"  {cond_temp} = icmp ne i32 {cond_value}, 0")
                    cond = cond_temp
                    self.i1_temporaries.add(cond_temp)
            else:
                # Already a temporary (shouldn't happen)
                cond = cond_value
            
            then_label = self.label_map.get(operands[1])
            else_label = self.label_map.get(operands[2])
            # Handle entry block (no label) - shouldn't happen for branches
            if then_label is None:
                then_label = "entry"
            if else_label is None:
                else_label = "entry"
            self.emit(f"  br i1 {cond}, label %{then_label}, label %{else_label}")
        
        elif op == Op.JUMP:
            # Unconditional jump: br label %target
            target_label = self.label_map.get(operands[0])
            # Handle entry block (no label) - shouldn't happen for jumps
            if target_label is None:
                target_label = "entry"
            self.emit(f"  br label %{target_label}")
        
        elif op == Op.RETURN:
            # Return void: ret void
            self.emit("  ret void")
        
        elif op == Op.RETVAL:
            # Return value: ret type %value
            value = self.get_llvm_value(operands[0])
            return_type = self.type_to_llvm(self.current_function.return_type)
            
            # If the return type is i8 and the value is i32 (temporary or constant), truncate it
            if return_type == "i8":
                if value.startswith('%'):
                    # It's a temporary - assume it's i32 and truncate to i8
                    trunc_temp = self.new_llvm_temp()
                    self.emit(f"  {trunc_temp} = trunc i32 {value} to i8")
                    value = trunc_temp
                else:
                    # It's a constant - create i8 constant directly
                    # Constants can be used directly, but to be safe, create a trunc
                    # Actually, for constants, we can use them directly if they fit in i8
                    # But to be consistent and handle all cases, create a temporary
                    const_temp = self.new_llvm_temp()
                    self.emit(f"  {const_temp} = add i32 0, {value}")
                    trunc_temp = self.new_llvm_temp()
                    self.emit(f"  {trunc_temp} = trunc i32 {const_temp} to i8")
                    value = trunc_temp
            
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

