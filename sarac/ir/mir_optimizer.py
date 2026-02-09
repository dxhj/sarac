"""
MIR (Mid-level Intermediate Representation) Optimizer.

This module provides various optimization passes for MIR code:
- Dead code elimination (unreachable blocks)
- Constant folding and propagation
- Dead store elimination
- Empty block removal
- Common subexpression elimination
"""

from sarac.ir.mir import MIRFunction, BasicBlock, Instruction, Op


class MIROptimizer:
    """Main optimizer class that applies various optimization passes."""
    
    def __init__(self):
        self.optimizations = []
    
    def optimize(self, mir_func: MIRFunction) -> MIRFunction:
        """
        Apply all optimization passes to a MIR function.
        
        Args:
            mir_func: The MIR function to optimize
            
        Returns:
            The optimized MIR function (modified in place)
        """
        # Build control flow graph
        self._build_cfg(mir_func)
        
        # Apply optimization passes
        # Run multiple iterations until no more changes
        changed = True
        iteration = 0
        max_iterations = 10
        
        while changed and iteration < max_iterations:
            changed = False
            iteration += 1
            
            # Remove instructions after return/jump/branch
            if self._remove_dead_instructions(mir_func):
                changed = True
            
            # Dead code elimination (unreachable blocks)
            if self._remove_unreachable_blocks(mir_func):
                changed = True
                self._build_cfg(mir_func)  # Rebuild CFG after removing blocks
            
            # Constant folding
            if self._constant_folding(mir_func):
                changed = True
            
            # Dead store elimination
            if self._dead_store_elimination(mir_func):
                changed = True
            
            # Remove empty blocks
            if self._remove_empty_blocks(mir_func):
                changed = True
                self._build_cfg(mir_func)  # Rebuild CFG after removing blocks
        
        return mir_func
    
    def _build_cfg(self, mir_func: MIRFunction):
        """Build control flow graph by setting predecessors and successors."""
        # Clear existing CFG information
        for block in mir_func.blocks:
            block.predecessors = []
            block.successors = []
        
        # Build label to block mapping
        label_to_block = {}
        for block in mir_func.blocks:
            if block.label:
                label_to_block[block.label] = block
        
        # Find entry block
        entry_block = None
        for block in mir_func.blocks:
            if block.label == "entry":
                entry_block = block
                break
        if not entry_block and mir_func.blocks:
            entry_block = mir_func.blocks[0]
        
        mir_func.entry_block = entry_block
        
        # Build CFG by analyzing instructions
        for block in mir_func.blocks:
            for instr in block.instructions:
                if instr.op == Op.JUMP:
                    # Unconditional jump
                    if len(instr.operands) > 0:
                        target_label = instr.operands[0]
                        if target_label in label_to_block:
                            target_block = label_to_block[target_label]
                            if target_block not in block.successors:
                                block.successors.append(target_block)
                            if block not in target_block.predecessors:
                                target_block.predecessors.append(block)
                
                elif instr.op == Op.BRANCH:
                    # Conditional branch: operands are (condition, true_label, false_label)
                    if len(instr.operands) >= 2:
                        true_label = instr.operands[1]
                        false_label = instr.operands[2] if len(instr.operands) > 2 else None
                        
                        if true_label in label_to_block:
                            target_block = label_to_block[true_label]
                            if target_block not in block.successors:
                                block.successors.append(target_block)
                            if block not in target_block.predecessors:
                                target_block.predecessors.append(block)
                        
                        if false_label and false_label in label_to_block:
                            target_block = label_to_block[false_label]
                            if target_block not in block.successors:
                                block.successors.append(target_block)
                            if block not in target_block.predecessors:
                                target_block.predecessors.append(block)
                
                elif instr.op in (Op.RETURN, Op.RETVAL):
                    # Return terminates the block
                    pass
        
        # Add entry block as predecessor of first reachable blocks
        if entry_block:
            # Entry block's successors are already set by jump/branch instructions
            pass
    
    def _remove_dead_instructions(self, mir_func: MIRFunction) -> bool:
        """
        Remove instructions that appear after return/jump/branch (dead code).
        
        Returns:
            True if any instructions were removed, False otherwise
        """
        changed = False
        
        for block in mir_func.blocks:
            new_instructions = []
            for instr in block.instructions:
                new_instructions.append(instr)
                # If this is a terminating instruction, stop here
                if instr.op in (Op.RETURN, Op.RETVAL, Op.JUMP, Op.BRANCH):
                    # Remove any remaining instructions after this one
                    if len(new_instructions) < len(block.instructions):
                        changed = True
                    break
            
            if len(new_instructions) < len(block.instructions):
                block.instructions = new_instructions
                changed = True
        
        return changed
    
    def _remove_unreachable_blocks(self, mir_func: MIRFunction) -> bool:
        """
        Remove unreachable basic blocks (dead code elimination).
        
        Returns:
            True if any blocks were removed, False otherwise
        """
        if not mir_func.blocks:
            return False
        
        # Find all reachable blocks using DFS from entry block
        reachable = set()
        to_visit = []
        
        # Find entry block
        entry_block = None
        for block in mir_func.blocks:
            if block.label == "entry":
                entry_block = block
                break
        if not entry_block and mir_func.blocks:
            entry_block = mir_func.blocks[0]
        
        if entry_block:
            to_visit.append(entry_block)
        
        while to_visit:
            block = to_visit.pop()
            if block in reachable:
                continue
            reachable.add(block)
            
            # Add successors to visit list
            for succ in block.successors:
                if succ not in reachable:
                    to_visit.append(succ)
        
        # Remove unreachable blocks
        original_count = len(mir_func.blocks)
        mir_func.blocks = [b for b in mir_func.blocks if b in reachable]
        
        return len(mir_func.blocks) < original_count
    
    def _constant_folding(self, mir_func: MIRFunction) -> bool:
        """
        Perform constant folding: evaluate constant expressions at compile time.
        
        Returns:
            True if any optimizations were made, False otherwise
        """
        changed = False
        
        # Track constant values for temporaries
        constants = {}  # temp -> constant value
        
        for block in mir_func.blocks:
            new_instructions = []
            
            for instr in block.instructions:
                # Skip control flow instructions
                if instr.op in (Op.JUMP, Op.BRANCH, Op.RETURN, Op.RETVAL, Op.CALL, Op.PARAM):
                    new_instructions.append(instr)
                    continue
                
                # Handle constant loading
                if instr.op == Op.CONST:
                    if instr.result and len(instr.operands) > 0:
                        constants[instr.result] = instr.operands[0]
                    new_instructions.append(instr)
                    continue
                
                # Try to fold operations with constant operands
                if instr.op in (Op.ADD, Op.SUB, Op.MUL, Op.DIV, Op.MOD):
                    if len(instr.operands) >= 2:
                        left = instr.operands[0]
                        right = instr.operands[1]
                        
                        # Check if both operands are constants
                        left_val = constants.get(left) if isinstance(left, str) else (left if isinstance(left, (int, float)) else None)
                        right_val = constants.get(right) if isinstance(right, str) else (right if isinstance(right, (int, float)) else None)
                        
                        # Convert string numbers to actual numbers
                        if isinstance(left_val, str):
                            try:
                                left_val = int(left_val) if left_val.isdigit() or (left_val.startswith('-') and left_val[1:].isdigit()) else float(left_val)
                            except (ValueError, AttributeError):
                                pass
                        if isinstance(right_val, str):
                            try:
                                right_val = int(right_val) if right_val.isdigit() or (right_val.startswith('-') and right_val[1:].isdigit()) else float(right_val)
                            except (ValueError, AttributeError):
                                pass
                        
                        if left_val is not None and right_val is not None and isinstance(left_val, (int, float)) and isinstance(right_val, (int, float)):
                            # Fold the operation
                            try:
                                if instr.op == Op.ADD:
                                    result = left_val + right_val
                                elif instr.op == Op.SUB:
                                    result = left_val - right_val
                                elif instr.op == Op.MUL:
                                    result = left_val * right_val
                                elif instr.op == Op.DIV:
                                    if right_val == 0:
                                        # Don't fold division by zero
                                        new_instructions.append(instr)
                                        continue
                                    # Use integer division for integer types
                                    if isinstance(left_val, int) and isinstance(right_val, int):
                                        result = left_val // right_val
                                    else:
                                        result = left_val / right_val
                                elif instr.op == Op.MOD:
                                    if right_val == 0:
                                        # Don't fold modulo by zero
                                        new_instructions.append(instr)
                                        continue
                                    result = left_val % right_val
                                
                                # Replace with constant load
                                const_instr = Instruction(Op.CONST, result)
                                const_instr.result = instr.result
                                new_instructions.append(const_instr)
                                if instr.result:
                                    constants[instr.result] = result
                                changed = True
                                continue
                            except (ZeroDivisionError, TypeError):
                                # Can't fold, keep original
                                pass
                
                # Handle unary operations
                elif instr.op in (Op.NEG, Op.NOT):
                    if len(instr.operands) >= 1:
                        operand = instr.operands[0]
                        operand_val = constants.get(operand) if isinstance(operand, str) else (operand if isinstance(operand, (int, float)) else None)
                        
                        # Convert string numbers to actual numbers
                        if isinstance(operand_val, str):
                            try:
                                operand_val = int(operand_val) if operand_val.isdigit() or (operand_val.startswith('-') and operand_val[1:].isdigit()) else float(operand_val)
                            except (ValueError, AttributeError):
                                pass
                        
                        if operand_val is not None and isinstance(operand_val, (int, float)):
                            try:
                                if instr.op == Op.NEG:
                                    result = -operand_val
                                elif instr.op == Op.NOT:
                                    result = 0 if operand_val else 1
                                
                                const_instr = Instruction(Op.CONST, result)
                                const_instr.result = instr.result
                                new_instructions.append(const_instr)
                                if instr.result:
                                    constants[instr.result] = result
                                changed = True
                                continue
                            except (TypeError, ValueError):
                                pass
                
                # Handle comparisons
                elif instr.op in (Op.EQ, Op.NE, Op.LT, Op.LE, Op.GT, Op.GE):
                    if len(instr.operands) >= 2:
                        left = instr.operands[0]
                        right = instr.operands[1]
                        
                        left_val = constants.get(left) if isinstance(left, str) else (left if isinstance(left, (int, float)) else None)
                        right_val = constants.get(right) if isinstance(right, str) else (right if isinstance(right, (int, float)) else None)
                        
                        # Convert string numbers to actual numbers
                        if isinstance(left_val, str):
                            try:
                                left_val = int(left_val) if left_val.isdigit() or (left_val.startswith('-') and left_val[1:].isdigit()) else float(left_val)
                            except (ValueError, AttributeError):
                                pass
                        if isinstance(right_val, str):
                            try:
                                right_val = int(right_val) if right_val.isdigit() or (right_val.startswith('-') and right_val[1:].isdigit()) else float(right_val)
                            except (ValueError, AttributeError):
                                pass
                        
                        if left_val is not None and right_val is not None and isinstance(left_val, (int, float)) and isinstance(right_val, (int, float)):
                            try:
                                if instr.op == Op.EQ:
                                    result = 1 if left_val == right_val else 0
                                elif instr.op == Op.NE:
                                    result = 1 if left_val != right_val else 0
                                elif instr.op == Op.LT:
                                    result = 1 if left_val < right_val else 0
                                elif instr.op == Op.LE:
                                    result = 1 if left_val <= right_val else 0
                                elif instr.op == Op.GT:
                                    result = 1 if left_val > right_val else 0
                                elif instr.op == Op.GE:
                                    result = 1 if left_val >= right_val else 0
                                
                                const_instr = Instruction(Op.CONST, result)
                                const_instr.result = instr.result
                                new_instructions.append(const_instr)
                                if instr.result:
                                    constants[instr.result] = result
                                changed = True
                                continue
                            except (TypeError, ValueError):
                                pass
                
                # Handle LOAD - if variable was stored with a constant, propagate it
                elif instr.op == Op.LOAD:
                    # For now, we don't track variable values across stores
                    # This would require more sophisticated analysis
                    new_instructions.append(instr)
                    continue
                
                # Handle STORE - invalidate constant for that variable
                elif instr.op == Op.STORE:
                    # When we store, we lose track of variable's constant value
                    # Could be enhanced with SSA or value numbering
                    new_instructions.append(instr)
                    continue
                
                # Default: keep instruction
                new_instructions.append(instr)
            
            block.instructions = new_instructions
        
        return changed
    
    def _dead_store_elimination(self, mir_func: MIRFunction) -> bool:
        """
        Remove stores to variables that are never read before the next store.
        
        Returns:
            True if any stores were removed, False otherwise
        """
        changed = False
        
        for block in mir_func.blocks:
            # Track last store to each variable
            last_store = {}  # var_name -> (index, instruction)
            loads = set()  # Set of variables that are loaded
            
            # First pass: find all loads
            for i, instr in enumerate(block.instructions):
                if instr.op == Op.LOAD and len(instr.operands) > 0:
                    var_name = instr.operands[0]
                    loads.add(var_name)
                elif instr.op == Op.STORE and len(instr.operands) >= 2:
                    var_name = instr.operands[0]
                    last_store[var_name] = (i, instr)
            
            # Second pass: remove stores that are never loaded
            new_instructions = []
            for i, instr in enumerate(block.instructions):
                if instr.op == Op.STORE and len(instr.operands) >= 2:
                    var_name = instr.operands[0]
                    # Check if this variable is ever loaded
                    if var_name not in loads:
                        # Check if this is the last store to this variable in this block
                        if var_name in last_store and last_store[var_name][0] == i:
                            # This store is dead - skip it
                            changed = True
                            continue
                
                new_instructions.append(instr)
            
            block.instructions = new_instructions
        
        return changed
    
    def _remove_empty_blocks(self, mir_func: MIRFunction) -> bool:
        """
        Remove empty basic blocks (except entry block) and redirect jumps.
        
        Returns:
            True if any blocks were removed, False otherwise
        """
        changed = False
        
        # Find empty blocks (blocks with no instructions or only labels)
        empty_blocks = []
        for block in mir_func.blocks:
            # Entry block should not be removed even if empty
            if block.label == "entry":
                continue
            
            # Check if block has no instructions (or only a jump to next block)
            if not block.instructions:
                empty_blocks.append(block)
            elif len(block.instructions) == 1 and block.instructions[0].op == Op.JUMP:
                # Block only has a jump - we can redirect predecessors
                empty_blocks.append(block)
        
        if not empty_blocks:
            return False
        
        # For each empty block, redirect all predecessors
        for empty_block in empty_blocks:
            # Find the target of the empty block
            target_label = None
            if empty_block.instructions:
                # Has a jump - get target
                jump_instr = empty_block.instructions[0]
                if len(jump_instr.operands) > 0:
                    target_label = jump_instr.operands[0]
            else:
                # No instructions - target is first successor
                if empty_block.successors:
                    target_label = empty_block.successors[0].label
            
            if not target_label:
                # Can't determine target, skip this block
                continue
            
            # Redirect all predecessors to jump to target instead
            for pred in empty_block.predecessors:
                for instr in pred.instructions:
                    if instr.op == Op.JUMP:
                        if len(instr.operands) > 0 and instr.operands[0] == empty_block.label:
                            instr.operands[0] = target_label
                            changed = True
                    elif instr.op == Op.BRANCH:
                        if len(instr.operands) >= 2:
                            if instr.operands[1] == empty_block.label:
                                instr.operands[1] = target_label
                                changed = True
                            if len(instr.operands) > 2 and instr.operands[2] == empty_block.label:
                                instr.operands[2] = target_label
                                changed = True
            
            # Remove the empty block
            if empty_block in mir_func.blocks:
                mir_func.blocks.remove(empty_block)
                changed = True
        
        return changed


def optimize_mir(mir_func: MIRFunction) -> MIRFunction:
    """
    Optimize a MIR function using all available optimizations.
    
    Args:
        mir_func: The MIR function to optimize
        
    Returns:
        The optimized MIR function
    """
    optimizer = MIROptimizer()
    return optimizer.optimize(mir_func)

