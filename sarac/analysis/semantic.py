from sarac.frontend.ast import Reference, BinaryOperator, UnaryOperator, Assignment, FunctionDefinition, Return, FunctionCall, Constant
from sarac.analysis.attributes import VariableAttributes
from sarac.analysis.types import generalize_type
from sarac.utils.error import Error


class SemanticsVisitor(object):
    def __init__(self):
        # Track current function's return type (functions can't be nested in this language)
        self.current_return_type = None
    
    def visit(self, node):
        if isinstance(node, FunctionDefinition):
            # Set the current function's return type
            self.current_return_type = node.return_type
            node.accept_children(self)
            # Clear when done with function
            self.current_return_type = None
            return
        
        if isinstance(node, Return):
            # Check return type against current function's return type
            if self.current_return_type is None:
                # Return statement outside of function (shouldn't happen, but handle gracefully)
                Error.type_error("return statement outside of function", 
                               node.coord.line if node.coord else 0, 
                               node.coord.column if node.coord else 0)
                node.accept_children(self)
                return
            
            expected_return_type = self.current_return_type
            
            if node.expression is None:
                # return; without expression
                # For now, we require a return value (no void type yet)
                Error.type_error("return statement must return a value", 
                               node.coord.line if node.coord else 0, 
                               node.coord.column if node.coord else 0)
            else:
                # return expression;
                node.expression.accept(self)
                actual_return_type = node.expression.type
                
                if actual_return_type is None:
                    Error.type_error("return expression has no type", 
                                   node.coord.line if node.coord else 0, 
                                   node.coord.column if node.coord else 0)
                elif actual_return_type != expected_return_type:
                    Error.type_error("return type mismatch: expected %s, got %s" % 
                                   (expected_return_type, actual_return_type),
                                   node.coord.line if node.coord else 0, 
                                   node.coord.column if node.coord else 0)
            return
        
        if isinstance(node, Constant):
            # Constants already have their type set in the parser
            # Just ensure we visit children (though constants typically have none)
            node.accept_children(self)
            return
        
        if isinstance(node, Reference):
            if node.attributes is not None and not is_data_object(node):
                Error.type_error("\"%s\" does not name a data object" % node.name, node.coord.line, node.coord.column)
            # Type should already be set by symbol table visitor
            # If not set, that's an error
            if not hasattr(node, 'type') or node.type is None:
                Error.type_error("variable \"%s\" has no type" % node.name, node.coord.line, node.coord.column)
            return

        if isinstance(node, UnaryOperator):
            node.accept_children(self)
            # Unary operators preserve the type of their operand
            if len(node.children) > 0 and node.children[0] is not None:
                node.type = node.children[0].type
            else:
                Error.type_error("unary operator has no operand", 
                               node.coord.line if node.coord else 0, 
                               node.coord.column if node.coord else 0)
            return

        if isinstance(node, BinaryOperator):
            # Visit children first to ensure their types are set
            node.accept_children(self)
            
            # Ensure both operands have types
            if not hasattr(node.children[0], 'type') or node.children[0].type is None:
                Error.type_error("left operand has no type", node.coord.line, node.coord.column)
                return
            if not hasattr(node.children[1], 'type') or node.children[1].type is None:
                Error.type_error("right operand has no type", node.coord.line, node.coord.column)
                return
            
            # Generalize the types (returns None for incompatible types like int + string)
            node.type = generalize_type(node.children[0].type, node.children[1].type)

            if node.type is None:
                type1_str = str(node.children[0].type) if node.children[0].type else "unknown"
                type2_str = str(node.children[1].type) if node.children[1].type else "unknown"
                Error.type_error("invalid types for binary operation: %s and %s" % (type1_str, type2_str), 
                               node.coord.line, node.coord.column)

            return

        if isinstance(node, FunctionCall):
            # Visit arguments first to get their types
            if node.arguments:
                node.arguments.accept_children(self)
            
            # Look up the function in symbol table
            if node.identifier.attributes is None:
                Error.type_error("function \"%s\" is not defined" % node.name,
                               node.coord.line if node.coord else 0,
                               node.coord.column if node.coord else 0)
            else:
                # Set the return type of the function call
                from sarac.analysis.attributes import FunctionAttributes
                if isinstance(node.identifier.attributes, FunctionAttributes):
                    node.type = node.identifier.attributes.type
                    node.attributes = node.identifier.attributes
                else:
                    Error.type_error("\"%s\" is not a function" % node.name,
                                   node.coord.line if node.coord else 0,
                                   node.coord.column if node.coord else 0)
            return

        if isinstance(node, Assignment):
            node.children[1].accept(self)
            if node.children[0].type is not node.children[1].type:
                Error.type_error("trying to assign different types", node.coord.line, node.coord.column)

            return

        node.accept_children(self)


def is_data_object(node):
    return type(node.attributes) == VariableAttributes
