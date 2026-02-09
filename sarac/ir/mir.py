"""
Mid-level Intermediate Representation (MIR) for the Sarac compiler.

MIR represents code as:
- Basic blocks (linear sequences of instructions)
- Three-address code (at most one operator per instruction)
- Explicit control flow (jumps, branches)
- Temporaries instead of named variables
"""

from sarac.frontend.ast import (
    TranslationUnitList, FunctionDefinition, Identifier,
    DeclarationList, StatementList, Assignment, Return,
    If, While, For, CompoundStatement, Constant, Reference,
    BinaryOperator, UnaryOperator, FunctionCall
)


class Instruction:
    """A single MIR instruction."""
    
    def __init__(self, op, *operands):
        self.op = op  # Operation kind (ADD, SUB, LOAD, STORE, etc.)
        self.operands = list(operands)  # Operands (can be temps, constants, labels)
        self.result = None  # Result temporary (if any)
        self.operand_types = None  # Optional: type information for operands (used for constants)
    
    def __repr__(self):
        if self.result:
            return f"{self.result} = {self.op}({', '.join(map(str, self.operands))})"
        else:
            return f"{self.op}({', '.join(map(str, self.operands))})"


class BasicBlock:
    """A basic block - a linear sequence of instructions with single entry/exit."""
    
    def __init__(self, label=None):
        self.label = label  # Block label (e.g., "BB0", "BB1")
        self.instructions = []  # List of instructions
        self.predecessors = []  # Predecessor blocks
        self.successors = []  # Successor blocks
    
    def add_instruction(self, instruction):
        """Add an instruction to this block."""
        self.instructions.append(instruction)
    
    def __repr__(self):
        lines = [f"{self.label}:"]
        for instr in self.instructions:
            lines.append(f"  {instr}")
        return "\n".join(lines)


class MIRFunction:
    """MIR representation of a function."""
    
    def __init__(self, name, return_type, parameters, parameter_types=None):
        self.name = name
        self.return_type = return_type
        self.parameters = parameters  # List of parameter names
        self.parameter_types = parameter_types or []  # List of parameter types
        self.blocks = []  # List of basic blocks
        self.entry_block = None  # Entry basic block
        self.temp_counter = 0  # Counter for generating temporaries
        self.label_counter = 0  # Counter for generating labels
    
    def new_temp(self):
        """Generate a new temporary variable name."""
        temp = f"t{self.temp_counter}"
        self.temp_counter += 1
        return temp
    
    def new_label(self):
        """Generate a new basic block label."""
        label = f"BB{self.label_counter}"
        self.label_counter += 1
        return label
    
    def create_block(self, label=None):
        """Create a new basic block."""
        if label is None:
            label = self.new_label()
        block = BasicBlock(label)
        self.blocks.append(block)
        return block
    
    def __repr__(self):
        lines = [f"function {self.name}({', '.join(self.parameters)}):"]
        for block in self.blocks:
            lines.append(str(block))
        return "\n".join(lines)


# Instruction operation kinds
class Op:
    """MIR instruction operations."""
    # Arithmetic
    ADD = "add"
    SUB = "sub"
    MUL = "mul"
    DIV = "div"
    MOD = "mod"
    NEG = "neg"
    
    # Comparisons
    EQ = "eq"
    NE = "ne"
    LT = "lt"
    LE = "le"
    GT = "gt"
    GE = "ge"
    
    # Logical
    AND = "and"
    OR = "or"
    NOT = "not"
    
    # Memory
    LOAD = "load"  # Load variable into temporary
    STORE = "store"  # Store temporary into variable
    CONST = "const"  # Load constant
    
    # Control flow
    BRANCH = "branch"  # Conditional branch
    JUMP = "jump"  # Unconditional jump
    RETURN = "return"  # Return from function
    RETVAL = "retval"  # Return with value
    
    # Function calls
    CALL = "call"  # Function call
    PARAM = "param"  # Parameter passing


class MIRGenerator:
    """Visitor that converts AST to MIR."""
    
    def __init__(self):
        self.functions = []  # List of MIRFunction objects
        self.current_function = None
        self.current_block = None
        self.var_to_temp = {}  # Map variable names to their current temp
    
    def visit(self, node):
        """Main visitor entry point."""
        if isinstance(node, TranslationUnitList):
            for unit in node.children:
                if unit:
                    unit.accept(self)
        
        elif isinstance(node, FunctionDefinition):
            self.visit_function_definition(node)
        
        else:
            node.accept_children(self)
    
    def visit_function_definition(self, node):
        """Convert a function definition to MIR."""
        # Get function name and return type
        func_name = node.children[0].name if isinstance(node.children[0], Identifier) else "unknown"
        return_type = node.return_type
        
        # Get parameters
        parameters = []
        parameter_types = []
        if len(node.children) > 1 and node.children[1]:
            param_list = node.children[1]
            for param in param_list.children:
                if hasattr(param, 'children') and param.children:
                    param_name = param.children[0].name
                    parameters.append(param_name)
                    # Get parameter type
                    if hasattr(param, 'type'):
                        parameter_types.append(param.type)
                    else:
                        parameter_types.append("int")  # Default
        
        # Create MIR function
        mir_func = MIRFunction(func_name, return_type, parameters, parameter_types)
        self.current_function = mir_func
        self.functions.append(mir_func)
        
        # Create entry block
        entry_block = mir_func.create_block("entry")
        self.current_block = entry_block
        
        # Process function body
        if len(node.children) > 2 and node.children[2]:
            self.visit_compound_statement(node.children[2])
        
        # If entry block doesn't end with return, add implicit return
        # (Only if we're still in the entry block - if we've branched, don't add)
        if self.current_block == entry_block:
            if not entry_block.instructions or entry_block.instructions[-1].op not in (Op.RETURN, Op.RETVAL, Op.JUMP, Op.BRANCH):
                # Check if we need a return value
                if return_type and str(return_type) != "void":
                    # Add return 0 for non-void functions (default)
                    temp = mir_func.new_temp()
                    const_instr = Instruction(Op.CONST, 0)
                    const_instr.result = temp
                    entry_block.add_instruction(const_instr)
                    ret_instr = Instruction(Op.RETVAL, temp)
                    entry_block.add_instruction(ret_instr)
                else:
                    entry_block.add_instruction(Instruction(Op.RETURN))
    
    def visit_compound_statement(self, node):
        """Process a compound statement (function body)."""
        # Process declarations first
        if len(node.children) > 0 and node.children[0]:
            decl_list = node.children[0]
            for decl in decl_list.children:
                if decl:
                    self.visit_declaration(decl)
        
        # Process statements
        if len(node.children) > 1 and node.children[1]:
            stmt_list = node.children[1]
            for stmt in stmt_list.children:
                if stmt:
                    self.visit_statement(stmt)
    
    def visit_declaration(self, node):
        """Process a variable declaration."""
        if not node.children:
            return
        
        var_name = node.children[0].name if isinstance(node.children[0], Identifier) else None
        if not var_name:
            return
        
        # If there's an initializer, process it
        if node.initializer and len(node.children) > 1:
            temp = self.visit_expression(node.children[1])
            # Store the initializer value into the variable
            store_instr = Instruction(Op.STORE, var_name, temp)
            self.current_block.add_instruction(store_instr)
            self.var_to_temp[var_name] = temp
    
    def visit_statement(self, node):
        """Process a statement."""
        if isinstance(node, Assignment):
            self.visit_assignment(node)
        elif isinstance(node, Return):
            self.visit_return(node)
        elif isinstance(node, If):
            self.visit_if(node)
        elif isinstance(node, While):
            self.visit_while(node)
        elif isinstance(node, For):
            self.visit_for(node)
        elif isinstance(node, FunctionCall):
            # Function call as a statement (e.g., print(...);)
            # Visit as expression to generate the call, but ignore the return value
            self.visit_expression(node)
        else:
            # Other statement types
            node.accept_children(self)
    
    def visit_assignment(self, node):
        """Process an assignment statement."""
        var_name = node.children[0].name if isinstance(node.children[0], Identifier) else None
        if not var_name:
            return
        
        # Evaluate the expression
        temp = self.visit_expression(node.children[1])
        
        # Store result into variable
        store_instr = Instruction(Op.STORE, var_name, temp)
        self.current_block.add_instruction(store_instr)
        self.var_to_temp[var_name] = temp
    
    def visit_return(self, node):
        """Process a return statement."""
        if node.expression:
            # Return with value
            temp = self.visit_expression(node.expression)
            ret_instr = Instruction(Op.RETVAL, temp)
            self.current_block.add_instruction(ret_instr)
        else:
            # Return without value
            ret_instr = Instruction(Op.RETURN)
            self.current_block.add_instruction(ret_instr)
    
    def visit_if(self, node):
        """Convert if statement to basic blocks with branches."""
        # Create blocks: then, else (if exists)
        then_block = self.current_function.create_block()
        else_block = self.current_function.create_block() if node.children[2] else None
        
        # Evaluate condition in current block
        cond_temp = self.visit_expression(node.children[0])
        
        # Store reference to block before branching
        entry_block = self.current_block
        
        # Process then block
        self.current_block = then_block
        if node.children[1]:
            # Handle compound statements or single statements
            if isinstance(node.children[1], CompoundStatement):
                self.visit_compound_statement(node.children[1])
            else:
                self.visit_statement(node.children[1])
        
        # Check if then block ends with return
        then_returns = False
        if self.current_block.instructions:
            last_instr = self.current_block.instructions[-1]
            then_returns = last_instr.op in (Op.RETURN, Op.RETVAL)
        
        # Process else block if it exists
        else_returns = False
        if else_block:
            self.current_block = else_block
            if node.children[2]:
                if isinstance(node.children[2], CompoundStatement):
                    self.visit_compound_statement(node.children[2])
                else:
                    self.visit_statement(node.children[2])
            
            # Check if else block ends with return
            if self.current_block.instructions:
                last_instr = self.current_block.instructions[-1]
                else_returns = last_instr.op in (Op.RETURN, Op.RETVAL)
        
        # Only create merge block if at least one branch doesn't return
        merge_block = None
        if not then_returns or (else_block and not else_returns):
            merge_block = self.current_function.create_block()
            
            # Add jumps to merge block from non-returning branches
            if not then_returns:
                self.current_block = then_block
                jump_instr = Instruction(Op.JUMP, merge_block.label)
                self.current_block.add_instruction(jump_instr)
            
            if else_block and not else_returns:
                self.current_block = else_block
                jump_instr = Instruction(Op.JUMP, merge_block.label)
                self.current_block.add_instruction(jump_instr)
        
        # Add branch instruction in entry block (must be last)
        if else_block:
            if merge_block:
                # At least one branch doesn't return - normal branching
                branch_instr = Instruction(Op.BRANCH, cond_temp, then_block.label, else_block.label)
            else:
                # Both branches return - branch doesn't matter, but we still need it
                branch_instr = Instruction(Op.BRANCH, cond_temp, then_block.label, else_block.label)
        else:
            # No else block
            if merge_block:
                branch_instr = Instruction(Op.BRANCH, cond_temp, then_block.label, merge_block.label)
            else:
                # Then returns, no else - branch to then
                branch_instr = Instruction(Op.BRANCH, cond_temp, then_block.label, then_block.label)
        
        entry_block.add_instruction(branch_instr)
        
        # Continue with merge block if it exists, otherwise execution ends
        if merge_block:
            self.current_block = merge_block
        # If no merge block, execution ends (both branches returned)
    
    def visit_while(self, node):
        """Convert while loop to basic blocks."""
        # Create blocks: condition, body, merge
        cond_block = self.current_function.create_block()
        body_block = self.current_function.create_block()
        merge_block = self.current_function.create_block()
        
        # Jump to condition block from current block
        jump_instr = Instruction(Op.JUMP, cond_block.label)
        self.current_block.add_instruction(jump_instr)
        
        # Process condition in condition block
        old_block = self.current_block
        self.current_block = cond_block
        cond_temp = self.visit_expression(node.children[0])
        
        # Branch based on condition
        branch_instr = Instruction(Op.BRANCH, cond_temp, body_block.label, merge_block.label)
        self.current_block.add_instruction(branch_instr)
        
        # Process body
        self.current_block = body_block
        self.visit_statement(node.children[1])
        # Jump back to condition
        jump_instr = Instruction(Op.JUMP, cond_block.label)
        self.current_block.add_instruction(jump_instr)
        
        # Continue with merge block
        self.current_block = merge_block
    
    def visit_for(self, node):
        """Convert for loop to basic blocks."""
        # Create blocks: init, condition, body, increment, merge
        init_block = self.current_function.create_block()
        cond_block = self.current_function.create_block()
        body_block = self.current_function.create_block()
        incr_block = self.current_function.create_block() if node.children[2] else None
        merge_block = self.current_function.create_block()
        
        # Process init (if exists)
        if node.children[0]:
            self.visit_statement(node.children[0])
        
        # Jump to condition
        jump_instr = Instruction(Op.JUMP, cond_block.label)
        self.current_block.add_instruction(jump_instr)
        
        # Process condition
        self.current_block = cond_block
        if node.children[1]:
            cond_temp = self.visit_expression(node.children[1])
            # Branch to body or merge
            if incr_block:
                branch_instr = Instruction(Op.BRANCH, cond_temp, body_block.label, merge_block.label)
            else:
                branch_instr = Instruction(Op.BRANCH, cond_temp, body_block.label, merge_block.label)
            self.current_block.add_instruction(branch_instr)
        else:
            # No condition - always enter body
            jump_instr = Instruction(Op.JUMP, body_block.label)
            self.current_block.add_instruction(jump_instr)
        
        # Process body
        self.current_block = body_block
        self.visit_statement(node.children[3])
        
        # Process increment (if exists)
        if incr_block:
            # Jump to increment
            jump_instr = Instruction(Op.JUMP, incr_block.label)
            self.current_block.add_instruction(jump_instr)
            self.current_block = incr_block
            self.visit_statement(node.children[2])
            # Jump back to condition
            jump_instr = Instruction(Op.JUMP, cond_block.label)
            self.current_block.add_instruction(jump_instr)
        else:
            # Jump back to condition
            jump_instr = Instruction(Op.JUMP, cond_block.label)
            self.current_block.add_instruction(jump_instr)
        
        # Continue with merge block
        self.current_block = merge_block
    
    def visit_expression(self, node):
        """Convert an expression to MIR and return a temporary."""
        if isinstance(node, Constant):
            # Load constant
            temp = self.current_function.new_temp()
            const_instr = Instruction(Op.CONST, node.value)
            const_instr.result = temp
            # Store type information for the constant
            if hasattr(node, 'type'):
                const_instr.operand_types = [node.type]
            self.current_block.add_instruction(const_instr)
            return temp
        
        elif isinstance(node, Reference):
            # Load variable
            var_name = node.name
            temp = self.current_function.new_temp()
            load_instr = Instruction(Op.LOAD, var_name)
            load_instr.result = temp
            self.current_block.add_instruction(load_instr)
            return temp
        
        elif isinstance(node, BinaryOperator):
            # Binary operation
            left_temp = self.visit_expression(node.children[0])
            right_temp = self.visit_expression(node.children[1])
            
            # Map operator to MIR op
            op_map = {
                '+': Op.ADD,
                '-': Op.SUB,
                '*': Op.MUL,
                '/': Op.DIV,
                '%': Op.MOD,
                '==': Op.EQ,
                '!=': Op.NE,
                '<': Op.LT,
                '<=': Op.LE,
                '>': Op.GT,
                '>=': Op.GE,
            }
            
            mir_op = op_map.get(node.op)
            if not mir_op:
                mir_op = node.op  # Fallback
            
            temp = self.current_function.new_temp()
            bin_instr = Instruction(mir_op, left_temp, right_temp)
            bin_instr.result = temp
            self.current_block.add_instruction(bin_instr)
            return temp
        
        elif isinstance(node, UnaryOperator):
            # Unary operation
            operand_temp = self.visit_expression(node.children[0])
            
            op_map = {
                '-': Op.NEG,
                '!': Op.NOT,
            }
            
            mir_op = op_map.get(node.op, node.op)
            temp = self.current_function.new_temp()
            unary_instr = Instruction(mir_op, operand_temp)
            unary_instr.result = temp
            self.current_block.add_instruction(unary_instr)
            return temp
        
        elif isinstance(node, FunctionCall):
            # Function call
            # First, evaluate arguments
            arg_temps = []
            if node.arguments:
                for arg in node.arguments.children:
                    arg_temp = self.visit_expression(arg)
                    # Pass parameter
                    param_instr = Instruction(Op.PARAM, arg_temp)
                    self.current_block.add_instruction(param_instr)
                    arg_temps.append(arg_temp)
            
            # Call function
            temp = self.current_function.new_temp()
            call_instr = Instruction(Op.CALL, node.name)
            call_instr.result = temp
            self.current_block.add_instruction(call_instr)
            return temp
        
        else:
            # Unknown expression type
            temp = self.current_function.new_temp()
            return temp
