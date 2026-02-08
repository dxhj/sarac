from sarac.frontend.ast import *


class PrintASTVisitor(object):
    def __init__(self):
        self.spaces = 0

    def visit(self, node):
        if isinstance(node, TranslationUnitList):
            print('* Visiting a translation unit list')
            node.accept_children(self)
        if isinstance(node, Declaration):
            self.spaces += 1
            print('* Visiting a declaration')
            node.accept_children(self)
            self.spaces -= 1
        elif isinstance(node, DeclarationList):
            self.spaces += 1
            print('* Visiting declarations')
            node.accept_children(self)
            self.spaces -= 1
        elif isinstance(node, ParameterList):
            self.spaces += 1
            print('* Visiting parameters')
            node.accept_children(self)
            self.spaces -= 1
        elif isinstance(node, StatementList):
            print('* Visiting statements')
            node.accept_children(self)
        elif isinstance(node, FunctionDefinition):
            print('* Visiting function definition')
            node.accept_children(self)
        elif isinstance(node, If):
            print('* Visiting if')
            node.accept_children(self)
        elif isinstance(node, While):
            print('* Visiting while')
            node.accept_children(self)
        elif isinstance(node, For):
            print('* Visiting for')
            node.accept_children(self)
        elif isinstance(node, CompoundStatement):
            print('* Visiting a compound statement')
            print('Symbols: ', node.names)
            node.accept_children(self)
        elif isinstance(node, Assignment):
            self.spaces += 1
            print('* Visiting an assignment')
            node.accept_children(self)
            self.spaces -= 1
        elif isinstance(node, Return):
            print('* Visiting a return statement')
            node.accept_children(self)
        elif isinstance(node, UnaryOperator):
            print(self.spaces * '\t', 'Visiting an unary operator', node.op)
            node.accept_children(self)
        elif isinstance(node, BinaryOperator):
            print(self.spaces * '\t', 'Visiting a binary operator: ', node.op)
            node.accept_children(self)
        elif isinstance(node, Identifier):
            print(self.spaces * '\t', "Visiting an identifier: ", node.name)
        elif isinstance(node, Reference):
            print(self.spaces * '\t', "Visiting a reference: ", node.name)
        elif isinstance(node, Constant):
            print(self.spaces * '\t', "Visiting a constant: ", node.value)


class PrettyPrintASTVisitor(object):
    """A pretty printer for AST that displays a tree-like structure."""
    
    def __init__(self):
        self.indent_string = "  "  # 2 spaces per level
        self.prefix_stack = []  # Track tree drawing characters for each level
    
    def _get_prefix(self, is_last):
        """Get the prefix for the current line based on the tree structure."""
        if len(self.prefix_stack) == 0:
            return ""
        
        prefix = ""
        # Build prefix from parent levels
        for was_last in self.prefix_stack[:-1]:
            if was_last:
                prefix += self.indent_string + " "
            else:
                prefix += "│" + self.indent_string
        
        # Add connector for current level
        if is_last:
            prefix += "└─"
        else:
            prefix += "├─"
        
        return prefix
    
    def _print_node(self, node_type, details="", is_last=True):
        """Print a node with proper tree formatting."""
        prefix = self._get_prefix(is_last)
        print(f"{prefix}{node_type}", end="")
        if details:
            print(f": {details}", end="")
        print()
    
    def _visit_children(self, node, is_last=True):
        """Helper to visit children with proper tree structure."""
        if not hasattr(node, 'children') or not node.children:
            return
        
        # Filter out None children
        valid_children = [c for c in node.children if c is not None]
        if not valid_children:
            return
        
        self.prefix_stack.append(is_last)
        
        for i, child in enumerate(valid_children):
            is_child_last = (i == len(valid_children) - 1)
            self.prefix_stack[-1] = is_child_last
            child.accept(self)
        
        self.prefix_stack.pop()
    
    def visit(self, node):
        if node is None:
            return
        
        # Default: assume this is the last child (will be overridden by parent)
        is_last = True
        if self.prefix_stack:
            is_last = self.prefix_stack[-1] if len(self.prefix_stack) > 0 else True
        
        if isinstance(node, TranslationUnitList):
            self._print_node("TranslationUnitList", is_last=is_last)
            self._visit_children(node, is_last)
        
        elif isinstance(node, FunctionDefinition):
            return_type = str(node.return_type) if hasattr(node, 'return_type') and node.return_type else "?"
            self._print_node("FunctionDefinition", f"return_type={return_type}", is_last=is_last)
            self._visit_children(node, is_last)
        
        elif isinstance(node, ParameterList):
            self._print_node("ParameterList", is_last=is_last)
            self._visit_children(node, is_last)
        
        elif isinstance(node, Declaration):
            decl_type = str(node.type) if hasattr(node, 'type') and node.type else "?"
            self._print_node("Declaration", f"type={decl_type}", is_last=is_last)
            self._visit_children(node, is_last)
        
        elif isinstance(node, DeclarationList):
            self._print_node("DeclarationList", is_last=is_last)
            self._visit_children(node, is_last)
        
        elif isinstance(node, StatementList):
            self._print_node("StatementList", is_last=is_last)
            self._visit_children(node, is_last)
        
        elif isinstance(node, CompoundStatement):
            symbol_count = len(node.names) if hasattr(node, 'names') and node.names else 0
            self._print_node("CompoundStatement", f"symbols={symbol_count}", is_last=is_last)
            self._visit_children(node, is_last)
        
        elif isinstance(node, Assignment):
            self._print_node("Assignment", is_last=is_last)
            self._visit_children(node, is_last)
        
        elif isinstance(node, Return):
            if node.expression is not None:
                self._print_node("Return", is_last=is_last)
                self._visit_children(node, is_last)
            else:
                self._print_node("Return", "no expression", is_last=is_last)
        
        elif isinstance(node, If):
            has_else = len(node.children) > 2 and node.children[2] is not None
            self._print_node("If", f"has_else={has_else}", is_last=is_last)
            self._visit_children(node, is_last)
        
        elif isinstance(node, While):
            self._print_node("While", is_last=is_last)
            self._visit_children(node, is_last)
        
        elif isinstance(node, For):
            self._print_node("For", is_last=is_last)
            self._visit_children(node, is_last)
        
        elif isinstance(node, BinaryOperator):
            self._print_node("BinaryOperator", f"op='{node.op}'", is_last=is_last)
            self._visit_children(node, is_last)
        
        elif isinstance(node, UnaryOperator):
            self._print_node("UnaryOperator", f"op='{node.op}'", is_last=is_last)
            self._visit_children(node, is_last)
        
        elif isinstance(node, Identifier):
            type_info = f", type={node.type}" if hasattr(node, 'type') and node.type else ""
            self._print_node("Identifier", f"name='{node.name}'{type_info}", is_last=is_last)
        
        elif isinstance(node, Reference):
            self._print_node("Reference", f"name='{node.name}'", is_last=is_last)
        
        elif isinstance(node, Constant):
            const_type = str(node.type) if hasattr(node, 'type') and node.type else "?"
            self._print_node("Constant", f"value={node.value}, type={const_type}", is_last=is_last)
        
        else:
            # Fallback for unknown node types
            node_type = type(node).__name__
            self._print_node(node_type, is_last=is_last)
            self._visit_children(node, is_last)
