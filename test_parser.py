
'''
This software is licensed under the GPL (GNU General Public License) version 2
as it appears here: http://www.gnu.org/copyleft/gpl.html
It is also included with this archive as `gpl.txt <gpl.txt>`_.
'''


import compiler
from compiler import ast
from compiler import consts

def walk_ast(tree):
    transformer = Visitor()
    see = dict.fromkeys('Class Function'.split())
    stack = [(tree, 0)]
    while stack:
        tree, seen = stack.pop()
        if not isinstance(tree, ast.Node):
            continue
        name = tree.__class__.__name__
        if name in see:
            if seen:
                yield 'end',
                continue
            
            if hasattr(transformer, 'visit'+name):
                yield 'start', getattr(transformer, 'visit'+name)(tree), tree.lineno
            if tree.doc:
                yield 'doc', tree.doc
            stack.append((tree, 1))
        x = list(tree.getChildren())
        x.reverse()
        for i in x:
            if isinstance(i, ast.Node):
                stack.append((i, 0))

class Visitor:
    def visitClass(self, node):
        if node.bases:
            return 'class %s(%s):'%(node.name, ', '.join([i.name for i in node.bases]))
        return 'class %s:'%node.name
    
    def visitFunction(self, node):
        args = node.argnames[:]
        args2 = []
        if node.kwargs:
            args2.append('**'+args.pop())
        if node.varargs:
            args2.append('*'+args.pop())
        if node.defaults:
            d = node.defaults[:]
            while d:
                args2.append(args.pop()+'=?')
                _ = d.pop()
        
        args2.reverse()
        args += args2
        
        return 'def %s(%s):'%(node.name, ', '.join(args))

if __name__ == '__main__':
    a = '''import a, b, c

#I am a comment

# todo: I am a todo

def foo(x, y=6, *args,
        **kwargs):
    return None

class bar:
    def __init__(self, foo=a, bar=b):
        """blah!"""
'''
    x = compiler.parse(a)
    for y in walk_ast(x, Visitor()):
        print y
