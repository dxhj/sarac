from sarac.frontend.ast import Expression, Constant, Reference, UnaryOperator, BinaryOperator


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
    def __init__(self):
        self.exprs = {}

    def visit(self, node):
        """
        Receives an expression node and transform it's children to a DAG representation
        :param node: Expression
        :return: None
        """
        if isinstance(node, Constant):
            node_repr = str(node)
            if node_repr not in self.exprs:
                self.exprs[node_repr] = node

        if isinstance(node, Reference):
            if node.name not in self.exprs:
                self.exprs[node.name] = node

        if isinstance(node, BinaryOperator):
            node.accept_children(self)

            node_repr = str(node)
            if node_repr not in self.exprs:
                self.exprs[node_repr] = node

            left_node_repr = str(node.children[0])
            right_node_repr = str(node.children[1])

            if left_node_repr in self.exprs:
                node.children[0] = self.exprs[left_node_repr]
            else:
                self.exprs[left_node_repr] = node.children[0]

            if right_node_repr in self.exprs:
                node.children[1] = self.exprs[right_node_repr]
            else:
                self.exprs[right_node_repr] = node.children[1]

        if isinstance(node, UnaryOperator):
            node.accept_children(self)

            node_repr = str(node)
            if node_repr not in self.exprs:
                self.exprs[node_repr] = node

            expr_repr = str(node.children[0])
            if expr_repr in self.exprs:
                self.exprs[expr_repr] = node.children[0]
