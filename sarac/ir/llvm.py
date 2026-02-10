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
        self.pending_param_types = []  # Types of parameters collected before a CALL
        self.alloca_instructions = []  # Alloca instructions to emit at function start
        self.i1_temporaries = set()  # Track which temporaries are i1 (from comparisons)
        self.string_literals = {}  # Map string values to (global_name, byte_length) tuples
        self.string_counter = 0  # Counter for string literal names
        self.print_format_strings = {}  # Map format strings to global constant names for print
        self.temp_types = {}  # Map MIR temps to their types (for print)
        self.mir_functions = {}  # Map function names to MIRFunction objects for parameter lookup
    
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
        elif type_str == "float":
            return "double"
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
        self.print_format_strings = {}
        
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
                            # Check if it's not a numeric string (int or float)
                            is_numeric = False
                            try:
                                float(value)  # Try to parse as number (int or float)
                                is_numeric = True
                            except (ValueError, TypeError):
                                pass
                            
                            if not is_numeric:
                                # Not a number, it's a string literal
                                if value not in self.string_literals:
                                    global_name = f"@.str{self.string_counter}"
                                    byte_length = len(value.encode('utf-8'))
                                    self.string_literals[value] = (global_name, byte_length)
                                    self.string_counter += 1
        
        # Emit string literal global constants
        for string_value, (global_name, byte_length) in self.string_literals.items():
            # Escape the string for LLVM IR
            escaped = string_value.replace('\\', '\\5C').replace('\n', '\\0A').replace('\t', '\\09').replace('\r', '\\0D').replace('"', '\\22').replace('\0', '\\00')
            # Create null-terminated string
            self.emit(f"{global_name} = private unnamed_addr constant [{byte_length + 1} x i8] c\"{escaped}\\00\"")
        
        if self.string_literals:
            self.emit("")  # Blank line after string literals
        
        # Track which functions are defined
        defined_functions = {func.name for func in mir_functions}
        
        # Collect all function calls to find which functions need declarations
        called_functions = set()
        print_called = False
        for func in mir_functions:
            for block in func.blocks:
                for instr in block.instructions:
                    if instr.op == Op.CALL:
                        func_name = instr.operands[0]
                        called_functions.add(func_name)
                        if func_name == "print":
                            print_called = True
        
        # Declare printf if print is called
        # Match clang's generated format exactly
        if print_called:
            # Use the exact format clang generates for printf
            self.emit("declare i32 @printf(i8* noundef, ...)")
            self.emit("")  # Blank line
        
        # Only declare functions that are called but not defined
        functions_to_declare = called_functions - defined_functions
        if functions_to_declare:
            # We need to declare external functions, but we don't have their signatures
            # For now, we'll skip declarations since we don't have enough info
            # In a real compiler, you'd look up function signatures from a symbol table
            pass
        
        # Build function lookup map
        for func in mir_functions:
            self.mir_functions[func.name] = func
        
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
        self.var_type_map = {}  # Map variable names to their LLVM types
        self.label_map = {}
        self.llvm_temp_counter = 1  # Start at 1 for LLVM IR numbering
        self.alloca_instructions = []
        self.i1_temporaries = set()  # Track which temporaries are i1 (from comparisons)
        self.temp_types = {}  # Reset temp types for this function
        self.pending_params = []  # Reset pending params
        self.pending_param_types = []  # Reset pending param types
        
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
        
        # Emit any format strings that will be used in this function
        # (We collect them as we generate, so we'll emit them on first use)
        # For now, we'll emit them when needed in _handle_print_call
        
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
        
        # Initialize variables to default values
        for var_name, alloca in self.var_to_llvm.items():
            var_type = func.var_types.get(var_name)
            if var_type:
                llvm_type = self.type_to_llvm(var_type)
                # Initialize string variables to null
                if llvm_type == "i8*":
                    null_ptr = self.new_llvm_temp()
                    self.emit(f"  {null_ptr} = getelementptr inbounds i8, i8* null, i32 0")
                    self.emit(f"  store i8* {null_ptr}, i8** {alloca}")
                # Other types can remain uninitialized (will be 0 by default)
        
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
                        # Get variable type from MIR function, default to i32
                        var_type = func.var_types.get(var_name)
                        llvm_type = self.type_to_llvm(var_type) if var_type else "i32"
                        alloca_temp = self.new_llvm_temp()
                        self.var_to_llvm[var_name] = alloca_temp
                        # Store the type mapping for later use
                        self.var_type_map[var_name] = llvm_type
                        self.alloca_instructions.append(f"{alloca_temp} = alloca {llvm_type}")
                elif instr.op == Op.STORE:
                    var_name = instr.operands[0]
                    if var_name not in self.var_to_llvm:
                        # Get variable type from MIR function, default to i32
                        var_type = func.var_types.get(var_name)
                        llvm_type = self.type_to_llvm(var_type) if var_type else "i32"
                        alloca_temp = self.new_llvm_temp()
                        self.var_to_llvm[var_name] = alloca_temp
                        # Store the type mapping for later use
                        self.var_type_map[var_name] = llvm_type
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
            # But exclude numeric strings (they should be treated as numbers, not strings)
            is_string = False
            if value in self.string_literals:
                # Check if it's actually a numeric string that was incorrectly added
                try:
                    float(value)  # Try to parse as number
                    # If it parses as a number, it's not a string literal
                    is_string = False
                except (ValueError, TypeError):
                    # Can't parse as number, so it's a real string literal
                    is_string = True
            
            # Also check type information if available
            if hasattr(instr, 'operand_types') and instr.operand_types and len(instr.operand_types) > 0:
                type_str = str(instr.operand_types[0]).lower()
                if type_str == "string":
                    is_string = True
                elif type_str == "float" or type_str == "int":
                    # Explicitly numeric type, not a string
                    is_string = False
            
            if result:
                if is_string:
                    # It's a string literal
                    global_name, byte_length = self.string_literals[value]
                    llvm_temp = self.new_llvm_temp()
                    # Get pointer to string: getelementptr to get i8* from [N x i8]*
                    self.emit(f"  {llvm_temp} = getelementptr inbounds [{byte_length + 1} x i8], [{byte_length + 1} x i8]* {global_name}, i32 0, i32 0")
                    self.temp_to_llvm[result] = llvm_temp
                    self.temp_types[result] = "string"  # Track type
                else:
                    # Number or character
                    llvm_value = self.get_llvm_value(value)
                    # Determine type from operand_types if available
                    if hasattr(instr, 'operand_types') and instr.operand_types and len(instr.operand_types) > 0:
                        type_str = str(instr.operand_types[0]).lower()
                        llvm_type = self.type_to_llvm(type_str)
                        self.temp_types[result] = type_str
                    else:
                        # Infer from value
                        if isinstance(value, float):
                            llvm_type = "double"
                            self.temp_types[result] = "float"
                        elif isinstance(value, str):
                            # Check if it's a float string (contains decimal point)
                            try:
                                float(value)
                                if '.' in value or 'e' in value.lower() or 'E' in value:
                                    llvm_type = "double"
                                    self.temp_types[result] = "float"
                                else:
                                    llvm_type = "i32"
                                    self.temp_types[result] = "int"
                            except ValueError:
                                # Check if it's a character literal
                                if len(value) >= 3 and value[0] == "'" and value[-1] == "'" or len(value) == 1:
                                    llvm_type = "i8"
                                    self.temp_types[result] = "char"
                                else:
                                    llvm_type = "i32"
                                    self.temp_types[result] = "int"
                        else:
                            llvm_type = "i32"
                            self.temp_types[result] = "int"
                    
                    llvm_temp = self.new_llvm_temp()
                    if llvm_type == "double":
                        # For floating point, use fadd or just the constant directly
                        self.emit(f"  {llvm_temp} = fadd {llvm_type} 0.0, {llvm_value}")
                    else:
                        self.emit(f"  {llvm_temp} = add {llvm_type} 0, {llvm_value}")
                    self.temp_to_llvm[result] = llvm_temp
        
        elif op == Op.LOAD:
            # Load variable: %t = load i32, i32* %var
            var_name = operands[0]
            # Get variable type from type map (set during collect_variables)
            llvm_type = self.var_type_map.get(var_name, "i32")
            llvm_var = self.var_to_llvm.get(var_name)
            if not llvm_var:
                # Should have been collected in first pass, but handle gracefully
                llvm_var = self.new_llvm_temp()
                self.var_to_llvm[var_name] = llvm_var
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = load {llvm_type}, {llvm_type}* {llvm_var}")
            if result:
                self.temp_to_llvm[result] = llvm_temp
                # Track type from variable
                var_type = self.current_function.var_types.get(var_name)
                if var_type:
                    type_str = str(var_type).lower()
                    self.temp_types[result] = type_str
                else:
                    self.temp_types[result] = "int"
        
        elif op == Op.STORE:
            # Store: store i32 %value, i32* %var
            var_name = operands[0]
            value_temp = operands[1]
            # Get variable type from type map (set during collect_variables)
            llvm_type = self.var_type_map.get(var_name, "i32")
            llvm_var = self.var_to_llvm.get(var_name)
            if not llvm_var:
                # Should have been collected in first pass, but handle gracefully
                llvm_var = self.new_llvm_temp()
                self.var_to_llvm[var_name] = llvm_var
            llvm_value = self.get_llvm_value(value_temp)
            
            # Get the type of the value being stored
            value_type = self.temp_types.get(value_temp, "int")
            value_llvm_type = self.type_to_llvm(value_type)
            
            # Handle type conversion if needed
            if llvm_type == "i8":
                # Storing to char (i8)
                if not llvm_value.startswith('%'):
                    # Constant - can use directly if it fits
                    try:
                        val = int(llvm_value)
                        if 0 <= val <= 255:
                            llvm_value = str(val)
                        else:
                            # Truncate constant
                            llvm_value = str(val & 0xFF)
                    except ValueError:
                        pass
                elif value_llvm_type == "i32":
                    # Temporary - need to truncate from i32 to i8
                    trunc_temp = self.new_llvm_temp()
                    self.emit(f"  {trunc_temp} = trunc i32 {llvm_value} to i8")
                    llvm_value = trunc_temp
            elif llvm_type == "double":
                # Storing to float (double)
                if value_llvm_type == "i32":
                    # Need to convert from i32 to double
                    if llvm_value.startswith('%'):
                        # Temporary - convert using sitofp
                        fpext_temp = self.new_llvm_temp()
                        self.emit(f"  {fpext_temp} = sitofp i32 {llvm_value} to double")
                        llvm_value = fpext_temp
                    else:
                        # Constant - can convert directly
                        try:
                            int_val = int(llvm_value)
                            llvm_value = str(float(int_val))
                        except ValueError:
                            pass
                # If value is already double, use it directly
            
            self.emit(f"  store {llvm_type} {llvm_value}, {llvm_type}* {llvm_var}")
        
        elif op == Op.ADD:
            # Add: %t = add i32 %a, %b or fadd double %a, %b
            a = self.get_llvm_value(operands[0])
            b = self.get_llvm_value(operands[1])
            
            # Check types - if either is string, convert pointer to int (hack to prevent segfault)
            a_type = self.temp_types.get(operands[0], "int")
            b_type = self.temp_types.get(operands[1], "int")
            
            # Convert string pointers to integers if needed (this is a workaround for invalid code)
            if a_type == "string" and a.startswith('%'):
                ptr_as_int = self.new_llvm_temp()
                self.emit(f"  {ptr_as_int} = ptrtoint i8* {a} to i32")
                a = ptr_as_int
                a_type = "int"
            if b_type == "string" and b.startswith('%'):
                ptr_as_int = self.new_llvm_temp()
                self.emit(f"  {ptr_as_int} = ptrtoint i8* {b} to i32")
                b = ptr_as_int
                b_type = "int"
            
            # Check if we need floating-point operations
            if a_type == "float" or b_type == "float":
                # Use floating-point addition
                llvm_type = "double"
                # Convert integer operands to double if needed
                if a_type != "float" and a.startswith('%'):
                    # Convert i32 to double
                    a_fp = self.new_llvm_temp()
                    self.emit(f"  {a_fp} = sitofp i32 {a} to double")
                    a = a_fp
                elif a_type != "float" and not a.startswith('%'):
                    # Constant - convert to float
                    try:
                        a = str(float(a))
                    except ValueError:
                        a_fp = self.new_llvm_temp()
                        self.emit(f"  {a_fp} = sitofp i32 {a} to double")
                        a = a_fp
                
                if b_type != "float" and b.startswith('%'):
                    # Convert i32 to double
                    b_fp = self.new_llvm_temp()
                    self.emit(f"  {b_fp} = sitofp i32 {b} to double")
                    b = b_fp
                elif b_type != "float" and not b.startswith('%'):
                    # Constant - convert to float
                    try:
                        b = str(float(b))
                    except ValueError:
                        b_fp = self.new_llvm_temp()
                        self.emit(f"  {b_fp} = sitofp i32 {b} to double")
                        b = b_fp
                
                llvm_temp = self.new_llvm_temp()
                self.emit(f"  {llvm_temp} = fadd {llvm_type} {a}, {b}")
                if result:
                    self.temp_to_llvm[result] = llvm_temp
                    self.temp_types[result] = "float"
            else:
                # Use integer addition
                llvm_type = "i32"
                llvm_temp = self.new_llvm_temp()
                self.emit(f"  {llvm_temp} = add {llvm_type} {a}, {b}")
                if result:
                    self.temp_to_llvm[result] = llvm_temp
                    self.temp_types[result] = "int"
        
        elif op == Op.SUB:
            # Subtract: %t = sub i32 %a, %b or fsub double %a, %b
            a = self.get_llvm_value(operands[0])
            b = self.get_llvm_value(operands[1])
            a_type = self.temp_types.get(operands[0], "int")
            b_type = self.temp_types.get(operands[1], "int")
            
            # Check if we need floating-point operations
            if a_type == "float" or b_type == "float":
                # Use floating-point subtraction
                llvm_type = "double"
                # Convert integer operands to double if needed
                if a_type != "float" and a.startswith('%'):
                    a_fp = self.new_llvm_temp()
                    self.emit(f"  {a_fp} = sitofp i32 {a} to double")
                    a = a_fp
                elif a_type != "float" and not a.startswith('%'):
                    try:
                        a = str(float(a))
                    except ValueError:
                        a_fp = self.new_llvm_temp()
                        self.emit(f"  {a_fp} = sitofp i32 {a} to double")
                        a = a_fp
                
                if b_type != "float" and b.startswith('%'):
                    b_fp = self.new_llvm_temp()
                    self.emit(f"  {b_fp} = sitofp i32 {b} to double")
                    b = b_fp
                elif b_type != "float" and not b.startswith('%'):
                    try:
                        b = str(float(b))
                    except ValueError:
                        b_fp = self.new_llvm_temp()
                        self.emit(f"  {b_fp} = sitofp i32 {b} to double")
                        b = b_fp
                
                llvm_temp = self.new_llvm_temp()
                self.emit(f"  {llvm_temp} = fsub {llvm_type} {a}, {b}")
                if result:
                    self.temp_to_llvm[result] = llvm_temp
                    self.temp_types[result] = "float"
            else:
                # Use integer subtraction
                llvm_type = "i32"
                llvm_temp = self.new_llvm_temp()
                self.emit(f"  {llvm_temp} = sub {llvm_type} {a}, {b}")
                if result:
                    self.temp_to_llvm[result] = llvm_temp
                    self.temp_types[result] = "int"
        
        elif op == Op.MUL:
            # Multiply: %t = mul i32 %a, %b or fmul double %a, %b
            a = self.get_llvm_value(operands[0])
            b = self.get_llvm_value(operands[1])
            a_type = self.temp_types.get(operands[0], "int")
            b_type = self.temp_types.get(operands[1], "int")
            
            # Check if we need floating-point operations
            if a_type == "float" or b_type == "float":
                # Use floating-point multiplication
                llvm_type = "double"
                # Convert integer operands to double if needed
                if a_type != "float" and a.startswith('%'):
                    a_fp = self.new_llvm_temp()
                    self.emit(f"  {a_fp} = sitofp i32 {a} to double")
                    a = a_fp
                elif a_type != "float" and not a.startswith('%'):
                    try:
                        a = str(float(a))
                    except ValueError:
                        a_fp = self.new_llvm_temp()
                        self.emit(f"  {a_fp} = sitofp i32 {a} to double")
                        a = a_fp
                
                if b_type != "float" and b.startswith('%'):
                    b_fp = self.new_llvm_temp()
                    self.emit(f"  {b_fp} = sitofp i32 {b} to double")
                    b = b_fp
                elif b_type != "float" and not b.startswith('%'):
                    try:
                        b = str(float(b))
                    except ValueError:
                        b_fp = self.new_llvm_temp()
                        self.emit(f"  {b_fp} = sitofp i32 {b} to double")
                        b = b_fp
                
                llvm_temp = self.new_llvm_temp()
                self.emit(f"  {llvm_temp} = fmul {llvm_type} {a}, {b}")
                if result:
                    self.temp_to_llvm[result] = llvm_temp
                    self.temp_types[result] = "float"
            else:
                # Use integer multiplication
                llvm_type = "i32"
                llvm_temp = self.new_llvm_temp()
                self.emit(f"  {llvm_temp} = mul {llvm_type} {a}, {b}")
                if result:
                    self.temp_to_llvm[result] = llvm_temp
                    self.temp_types[result] = "int"
        
        elif op == Op.DIV:
            # Divide: %t = sdiv i32 %a, %b or fdiv double %a, %b
            a = self.get_llvm_value(operands[0])
            b = self.get_llvm_value(operands[1])
            a_type = self.temp_types.get(operands[0], "int")
            b_type = self.temp_types.get(operands[1], "int")
            
            # Check if we need floating-point operations
            if a_type == "float" or b_type == "float":
                # Use floating-point division
                llvm_type = "double"
                # Convert integer operands to double if needed
                if a_type != "float" and a.startswith('%'):
                    a_fp = self.new_llvm_temp()
                    self.emit(f"  {a_fp} = sitofp i32 {a} to double")
                    a = a_fp
                elif a_type != "float" and not a.startswith('%'):
                    try:
                        a = str(float(a))
                    except ValueError:
                        a_fp = self.new_llvm_temp()
                        self.emit(f"  {a_fp} = sitofp i32 {a} to double")
                        a = a_fp
                
                if b_type != "float" and b.startswith('%'):
                    b_fp = self.new_llvm_temp()
                    self.emit(f"  {b_fp} = sitofp i32 {b} to double")
                    b = b_fp
                elif b_type != "float" and not b.startswith('%'):
                    try:
                        b = str(float(b))
                    except ValueError:
                        b_fp = self.new_llvm_temp()
                        self.emit(f"  {b_fp} = sitofp i32 {b} to double")
                        b = b_fp
                
                llvm_temp = self.new_llvm_temp()
                self.emit(f"  {llvm_temp} = fdiv {llvm_type} {a}, {b}")
                if result:
                    self.temp_to_llvm[result] = llvm_temp
                    self.temp_types[result] = "float"
            else:
                # Use integer division
                llvm_type = "i32"
                llvm_temp = self.new_llvm_temp()
                self.emit(f"  {llvm_temp} = sdiv {llvm_type} {a}, {b}")
                if result:
                    self.temp_to_llvm[result] = llvm_temp
                    self.temp_types[result] = "int"
        
        elif op == Op.MOD:
            # Modulo: %t = srem i32 %a, %b
            a = self.get_llvm_value(operands[0])
            b = self.get_llvm_value(operands[1])
            llvm_type = "i32"
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = srem {llvm_type} {a}, {b}")
            if result:
                self.temp_to_llvm[result] = llvm_temp
                # Modulo always produces int
                self.temp_types[result] = "int"
        
        elif op == Op.SHL:
            # Left shift: %t = shl i32 %a, %b
            a = self.get_llvm_value(operands[0])
            b = self.get_llvm_value(operands[1])
            llvm_type = "i32"
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = shl {llvm_type} {a}, {b}")
            if result:
                self.temp_to_llvm[result] = llvm_temp
                self.temp_types[result] = "int"
        
        elif op == Op.SHR:
            # Right shift (arithmetic): %t = ashr i32 %a, %b
            # Using arithmetic shift for signed integers
            a = self.get_llvm_value(operands[0])
            b = self.get_llvm_value(operands[1])
            llvm_type = "i32"
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = ashr {llvm_type} {a}, {b}")
            if result:
                self.temp_to_llvm[result] = llvm_temp
                self.temp_types[result] = "int"
        
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
                    # It's a temporary - check its type
                    value_type = self.temp_types.get(operands[0], "int")
                    value_llvm_type = self.type_to_llvm(value_type)
                    if value_llvm_type == "i32":
                        # Need to truncate from i32 to i8
                        trunc_temp = self.new_llvm_temp()
                        self.emit(f"  {trunc_temp} = trunc i32 {value} to i8")
                        value = trunc_temp
                    # If it's already i8, use it directly
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
            # Try to determine type from the operand
            param_type = self._get_operand_type(operands[0])
            self.pending_param_types.append(param_type)
        
        elif op == Op.CALL:
            # Function call: %t = call i32 @func(i32 %arg1, i32 %arg2, ...)
            func_name = operands[0]
            
            # Handle built-in print function specially
            if func_name == "print":
                self._handle_print_call()
                # print returns void, so no result temp needed
                return
            
            # Determine how many parameters this function expects
            expected_param_count = 0
            if func_name in self.mir_functions:
                expected_param_count = len(self.mir_functions[func_name].parameters)
            
            # Only consume the parameters that belong to this call
            # Parameters are collected in order, so we take the last N parameters
            if expected_param_count > 0:
                params = self.pending_params[-expected_param_count:]
                param_types = self.pending_param_types[-expected_param_count:] if len(self.pending_param_types) >= expected_param_count else []
                # Remove consumed parameters
                self.pending_params = self.pending_params[:-expected_param_count]
                self.pending_param_types = self.pending_param_types[:-expected_param_count] if len(self.pending_param_types) >= expected_param_count else []
            else:
                # Function takes no parameters, don't consume any
                params = []
                param_types = []
            
            # Get actual return type from function signature
            if func_name in self.mir_functions:
                func_return_type = self.mir_functions[func_name].return_type
                return_type = self.type_to_llvm(func_return_type)
            else:
                return_type = "i32"  # Default
            
            # Build parameter list with correct types
            if params:
                # Get parameter types from function signature
                param_type_strs = []
                if func_name in self.mir_functions and self.mir_functions[func_name].parameter_types:
                    param_type_strs = [self.type_to_llvm(pt) for pt in self.mir_functions[func_name].parameter_types]
                else:
                    # Default to i32 for all params
                    param_type_strs = ["i32"] * len(params)
                
                param_str = ", ".join([f"{pt} {p}" for pt, p in zip(param_type_strs, params)])
            else:
                param_str = ""
            
            llvm_temp = self.new_llvm_temp()
            self.emit(f"  {llvm_temp} = call {return_type} @{func_name}({param_str})")
            if result:
                self.temp_to_llvm[result] = llvm_temp
                # Track the return type of the function call
                if func_name in self.mir_functions:
                    func_return_type = self.mir_functions[func_name].return_type
                    if func_return_type:
                        type_str = str(func_return_type).lower()
                        if type_str == "char":
                            self.temp_types[result] = "char"
                        elif type_str == "string":
                            self.temp_types[result] = "string"
                        elif type_str == "float":
                            self.temp_types[result] = "float"
                        else:
                            self.temp_types[result] = "int"
                    else:
                        self.temp_types[result] = "int"
                else:
                    self.temp_types[result] = "int"  # Default
    
    def _get_operand_type(self, operand):
        """Try to determine the type of an operand (temp name or constant)."""
        # Check if it's a temporary that we've seen before
        if operand in self.temp_types:
            return self.temp_types[operand]
        
        # Check if it's a string literal (in string_literals)
        if isinstance(operand, str):
            if operand in self.string_literals:
                return "string"
            # Check if it's a character literal
            if len(operand) >= 3 and operand[0] == "'" and operand[-1] == "'":
                return "char"
            if len(operand) == 1:
                return "char"
            # Check if it's a temporary that points to a string (starts with @.str)
            # This would be the LLVM value, not the MIR temp
            if operand.startswith('@.str'):
                return "string"
            # Try to parse as number
            try:
                int(operand)
                return "int"
            except ValueError:
                try:
                    float(operand)
                    return "float"
                except ValueError:
                    pass
        
        # Default to int
        return "int"
    
    def _get_or_create_format_string(self, arg_type):
        """Get or create a format string constant for the given type. Returns the global name."""
        # Determine format string based on type
        # The format_str uses LLVM escape sequences: \0A = newline, \00 = null
        # "%d\0A\00" in LLVM IR represents: '%' (1) + 'd' (1) + '\n' (1) + '\0' (1) = 4 bytes
        # But we need to count the actual bytes in the final string
        if arg_type == "string":
            format_str = "%s\\0A\\00"  # "%s\n\0" 
            format_len = 4  # '%', 's', '\n', '\0'
        elif arg_type == "char":
            format_str = "%c\\0A\\00"  # "%c\n\0"
            format_len = 4  # '%', 'c', '\n', '\0'
        elif arg_type == "float":
            format_str = "%f\\0A\\00"  # "%f\n\0"
            format_len = 4  # '%', 'f', '\n', '\0'
        else:  # int (default)
            format_str = "%d\\0A\\00"  # "%d\n\0"
            format_len = 4  # '%', 'd', '\n', '\0'
        
        # Check if we already have this format string
        format_key = (format_str, format_len)
        if format_key not in self.print_format_strings:
            format_global = f"@.str.print{self.string_counter}"
            self.string_counter += 1
            self.print_format_strings[format_key] = (format_global, format_len, format_str)
            # Emit at global scope - insert before current function definition
            # Find the function definition line and insert before it
            func_def_line = None
            for i, line in enumerate(self.output):
                if line.startswith(f"define ") and f"@{self.current_function.name}(" in line:
                    func_def_line = i
                    break
            if func_def_line is not None:
                # Insert the format string before the function definition
                self.output.insert(func_def_line, f"{format_global} = private unnamed_addr constant [{format_len} x i8] c\"{format_str}\"")
            else:
                # Fallback: emit at end (shouldn't happen)
                self.emit(f"{format_global} = private unnamed_addr constant [{format_len} x i8] c\"{format_str}\"")
        else:
            format_global, format_len, _ = self.print_format_strings[format_key]
        
        return format_global, format_len
    
    def _get_format_specifier(self, arg_type):
        """Get the format specifier character for a given type."""
        if arg_type == "string":
            return "%s"
        elif arg_type == "char":
            return "%c"
        elif arg_type == "float":
            return "%f"
        else:  # int (default)
            return "%d"
    
    def _handle_print_call(self):
        """Handle a call to the print built-in function."""
        # Use collected parameters
        params = self.pending_params
        param_types = self.pending_param_types
        self.pending_params = []  # Reset for next call
        self.pending_param_types = []  # Reset for next call
        
        if not params:
            # No arguments - print newline
            format_str = "\\0A\\00"  # "\n\0" = 2 chars
            format_len = 2
            format_key = (format_str, format_len)
            if format_key not in self.print_format_strings:
                format_global = f"@.str.print{self.string_counter}"
                self.string_counter += 1
                self.print_format_strings[format_key] = (format_global, format_len, format_str)
                # Emit at global scope - insert before current function definition
                func_def_line = None
                for i, line in enumerate(self.output):
                    if line.startswith(f"define ") and f"@{self.current_function.name}(" in line:
                        func_def_line = i
                        break
                if func_def_line is not None:
                    self.output.insert(func_def_line, f"{format_global} = private unnamed_addr constant [{format_len} x i8] c\"{format_str}\"")
                else:
                    self.emit(f"{format_global} = private unnamed_addr constant [{format_len} x i8] c\"{format_str}\"")
            else:
                format_global, format_len, _ = self.print_format_strings[format_key]
            
            format_ptr = self.new_llvm_temp()
            self.emit(f"  {format_ptr} = getelementptr inbounds [{format_len} x i8], [{format_len} x i8]* {format_global}, i32 0, i32 0")
            printf_result = self.new_llvm_temp()
            self.emit(f"  {printf_result} = call i32 (i8*, ...) @printf(i8* noundef {format_ptr})")
            return
        
        # Build combined format string from all argument types
        format_specs = []
        for i, arg_type in enumerate(param_types if param_types else ["int"] * len(params)):
            format_specs.append(self._get_format_specifier(arg_type))
        
        # Combine format specifiers and add newline
        format_str_parts = "".join(format_specs) + "\\0A\\00"  # Add newline and null terminator
        # Calculate length: each format specifier is 2 chars (%s, %d, %c, %f), plus \n (1 char) and \0 (1 char)
        format_len = len(format_specs) * 2 + 2  # 2 chars per specifier + \n + \0
        
        # Escape the format string for LLVM IR
        format_str = format_str_parts
        
        # Get or create format string
        format_key = (format_str, format_len)
        if format_key not in self.print_format_strings:
            format_global = f"@.str.print{self.string_counter}"
            self.string_counter += 1
            self.print_format_strings[format_key] = (format_global, format_len, format_str)
            # Emit at global scope - insert before current function definition
            func_def_line = None
            for i, line in enumerate(self.output):
                if line.startswith(f"define ") and f"@{self.current_function.name}(" in line:
                    func_def_line = i
                    break
            if func_def_line is not None:
                self.output.insert(func_def_line, f"{format_global} = private unnamed_addr constant [{format_len} x i8] c\"{format_str}\"")
            else:
                self.emit(f"{format_global} = private unnamed_addr constant [{format_len} x i8] c\"{format_str}\"")
        else:
            format_global, format_len, _ = self.print_format_strings[format_key]
        
        # Get pointer to format string
        format_ptr = self.new_llvm_temp()
        self.emit(f"  {format_ptr} = getelementptr inbounds [{format_len} x i8], [{format_len} x i8]* {format_global}, i32 0, i32 0")
        
        # Prepare all arguments with correct types
        printf_args = []
        for i, arg in enumerate(params):
            arg_type = param_types[i] if i < len(param_types) else "int"
            # Convert MIR temporary to LLVM value
            arg_value = self.get_llvm_value(arg)
            
            # Prepare character arguments
            if arg_type == "char":
                if not arg_value.startswith('%'):
                    # Character constant - convert to integer
                    if len(arg_value) >= 3 and arg_value[0] == "'" and arg_value[-1] == "'":
                        char_str = arg_value[1:-1]
                        if len(char_str) == 1:
                            arg_value = str(ord(char_str))
                        elif len(char_str) == 2 and char_str[0] == '\\':
                            escape_map = {'n': '\n', 't': '\t', 'r': '\r', '\\': '\\', "'": "'", '"': '"'}
                            char = escape_map.get(char_str[1], char_str[1])
                            arg_value = str(ord(char))
                    elif len(arg_value) == 1:
                        arg_value = str(ord(arg_value))
                else:
                    # Temporary holding char (i8) - zero-extend to i32 for printf
                    zext_temp = self.new_llvm_temp()
                    self.emit(f"  {zext_temp} = zext i8 {arg_value} to i32")
                    arg_value = zext_temp
            
            # Determine LLVM type and format for printf call
            if arg_type == "string":
                printf_args.append(f"i8* noundef {arg_value}")
            elif arg_type == "float":
                if arg_value.startswith('%'):
                    # Check if it's already a double or needs conversion
                    # Check recent output to see if this value was created with floating-point operations
                    is_double = False
                    for line in reversed(self.output):
                        if (f"{arg_value} = fadd" in line or 
                            f"{arg_value} = fsub" in line or
                            f"{arg_value} = fmul" in line or
                            f"{arg_value} = fdiv" in line or
                            f"{arg_value} = load double" in line):
                            is_double = True
                            break
                        # Stop searching if we hit a different instruction for this value
                        if f"{arg_value} = " in line and not any(op in line for op in ["fadd", "fsub", "fmul", "fdiv", "load double"]):
                            break
                    
                    if is_double:
                        # Already a double (created with fadd or load double), use directly
                        printf_args.append(f"double noundef {arg_value}")
                    else:
                        # Convert i32 temp to double
                        fpext_temp = self.new_llvm_temp()
                        self.emit(f"  {fpext_temp} = sitofp i32 {arg_value} to double")
                        printf_args.append(f"double noundef {fpext_temp}")
                else:
                    # Constant - check if it's a float constant
                    try:
                        float_val = float(arg_value)
                        printf_args.append(f"double noundef {arg_value}")
                    except ValueError:
                        # Not a float constant, convert from int
                        fpext_temp = self.new_llvm_temp()
                        self.emit(f"  {fpext_temp} = sitofp i32 {arg_value} to double")
                        printf_args.append(f"double noundef {fpext_temp}")
            else:  # int or char (both passed as i32)
                printf_args.append(f"i32 noundef {arg_value}")
        
        # Call printf with all arguments
        printf_result = self.new_llvm_temp()
        if printf_args:
            args_str = ", ".join(printf_args)
            self.emit(f"  {printf_result} = call i32 (i8*, ...) @printf(i8* noundef {format_ptr}, {args_str})")
        else:
            self.emit(f"  {printf_result} = call i32 (i8*, ...) @printf(i8* noundef {format_ptr})")
    
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
            # Try to parse as number FIRST (before treating single chars as character literals)
            # This fixes the bug where "1" was being treated as a character
            try:
                # Try integer first
                int_val = int(operand)
                return str(int_val)
            except ValueError:
                # Try float
                try:
                    float_val = float(operand)
                    return str(float_val)
                except ValueError:
                    pass
            # Check if it's a single character (character literal value from Constant node)
            # Only treat as character if it's NOT a digit
            if len(operand) == 1 and not operand.isdigit():
                # This is a character literal value (like 'a' stored as the string 'a')
                return str(ord(operand))
        
        # Check if it's an integer
        if isinstance(operand, int):
            return str(operand)
        
        # Otherwise, treat as constant (might be a variable name or other)
        return str(operand)

