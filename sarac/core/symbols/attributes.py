class Attributes(object):
    def __init__(self):
        self.name = None
        self.type = None


class FunctionAttributes(Attributes):
    def __init__(self):
        super(FunctionAttributes, self).__init__()
        self.parameters = None

    def __repr__(self):
        return "<FunctionAttributes, {} {}({})>".format(self.type,
                                                        self.name,
                                                        [str(decl.children[0].type) + " " + decl.children[0].name \
                                                         for decl in self.parameters.children])


class VariableAttributes(Attributes):
    def __init__(self):
        super(VariableAttributes, self).__init__()
        self.offset = None

    def __repr__(self):
        return "<VariableAttributes, %s %s:%d>" % (self.type, self.name, self.offset)
