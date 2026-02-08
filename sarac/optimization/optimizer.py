from sarac.frontend.ast import Expression, Constant, Reference, UnaryOperator, BinaryOperator, FunctionCall


class OptimizerVisitor(object):
    def visit(self, node):
        """
        Receives an expression and optimizes it removing redundancies by constructing a DAG
        :param node: Node
        :return: None
        """
        if isinstance(node, Expression):
            build_dag = BuildDAGVisitor()
            node.accept(build_dag)
            return

        node.accept_children(self)


class BuildDAGVisitor(object):
    """
    Builds a DAG (Directed Acyclic Graph) from the AST by sharing common subexpressions.
    
    Algorithm:
    1. Traverse expressions bottom-up (post-order)
    2. For each expression, create a canonical key based on its structure
    3. If key exists, replace with existing node (sharing)
    4. Otherwise, add to DAG table for future sharing
    """
    
    def __init__(self):
        # Maps canonical representation -> node
        # Same canonical rep means same computation, so we share the node
        self.dag_table = {}

    def _canonical_key(self, node):
        """
        Create a unique canonical key for an expression node.
        Expressions with the same key compute the same value and can be shared.
        """
        if isinstance(node, Constant):
            # Constants: key is (type, value)
            return ('const', str(node.type), node.value)
        
        elif isinstance(node, Reference):
            # Variables: key is variable name (assumes same variable = same value)
            # Note: This is a simplification - in reality, we'd need SSA or value numbering
            return ('ref', node.name)
        
        elif isinstance(node, UnaryOperator):
            # Unary ops: key is (op, child_key)
            child_key = self._canonical_key(node.children[0]) if node.children else None
            return ('unary', node.op, child_key)
        
        elif isinstance(node, BinaryOperator):
            # Binary ops: key is (op, left_key, right_key)
            left_key = self._canonical_key(node.children[0]) if len(node.children) > 0 else None
            right_key = self._canonical_key(node.children[1]) if len(node.children) > 1 else None
            return ('binary', node.op, left_key, right_key)
        
        elif isinstance(node, FunctionCall):
            # Function calls: key is (func_name, arg_keys...)
            # Note: Function calls with side effects shouldn't be shared, but we include for completeness
            arg_keys = []
            if node.arguments:
                for arg in node.arguments.children:
                    arg_keys.append(self._canonical_key(arg))
            return ('call', node.name, tuple(arg_keys))
        
        else:
            # Unknown expression type - use object id as fallback
            return ('unknown', id(node))

    def visit(self, node):
        """
        Transform expression tree into DAG by sharing common subexpressions.
        Processes children first (bottom-up), then optimizes current node.
        """
        # First, recursively process children to optimize them
        if hasattr(node, 'children'):
            for i, child in enumerate(node.children):
                if child and isinstance(child, Expression):
                    child.accept(self)
                    # After processing child, it might have been replaced with a shared node
                    # Get the canonical key of the (possibly replaced) child
                    child_key = self._canonical_key(child)
                    if child_key in self.dag_table:
                        # Replace with shared node
                        node.children[i] = self.dag_table[child_key]
                    else:
                        # Add to DAG table for future sharing
                        self.dag_table[child_key] = child

        # Now process the current node
        if isinstance(node, Expression):
            key = self._canonical_key(node)
            
            if key in self.dag_table:
                # This expression already exists - we could return the shared node
                # But we're modifying in-place, so we keep the current node structure
                # The sharing happens through children references
                pass
            else:
                # Add to DAG table for future sharing
                self.dag_table[key] = node
