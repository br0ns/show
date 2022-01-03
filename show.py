import inspect
import ast

TAB_WIDTH = 4

class Keyword(str): pass
class Positional(int): pass
class Evaluate(str): pass
class Verbatim(str): pass

def indentation(s):
    return len(s) - len(s.lstrip())

_cache = {}
def _get(this):
    call = this.f_back
    path = inspect.getsourcefile(call)
    key = (path, call.f_lineno)
    if key in _cache:
        return _cache[key]

    fd = open(path, 'r')
    def get():
        c = fd.read(1)
        if not c:
            raise EOFError
        return c

    lino = 1
    while True:
        c = get()
        if c == '\n':
            lino += 1
        if lino == call.f_lineno:
            break

    name = this.f_code.co_name
    i = 0
    while True:
        c = get()
        if c == '\n':
            raise Exception(f'Could not find call to {name} on line {lino} in {path}')
        if i == len(name):
            if c.isspace():
                continue
            elif c == '(':
                break
            else:
                i = 0
        elif c == name[i]:
            i += 1
        else:
            i = 0

    # TODO: better parsing
    code = name + '('
    offsets = [0]

    while True:
        c = get()
        if c == '\t':
            c = ' ' * TAB_WIDTH
        code += c
        if c == '\n':
            offsets += [len(code)]
        try:
            t = ast.parse(code)
            break
        except SyntaxError:
            continue

    def line_col_to_offset(lineno, col):
        return offsets[lineno - 1] + col

    def node_offset(node):
        return line_col_to_offset(node.lineno, node.col_offset)

    def node_end_offset(node):
        return line_col_to_offset(node.end_lineno, node.end_col_offset)

    def extract(node):
        return code[node_offset(node) : node_end_offset(node)]

    # Assert that this AST is in fact the function call we're looking for, and unwrap
    assert isinstance(t, ast.Module)
    assert len(t.body) == 1
    t = t.body[0]
    assert isinstance(t, ast.Expr)
    t = t.value
    assert isinstance(t, ast.Call)
    assert t.func.id == name

    template = []
    expansions = {}
    prev = 0
    def copy(pos):
        nonlocal prev, template
        if pos > prev:
            template += [Verbatim(code[prev:pos])]
            prev = pos
    def copy_to_start(node):
        copy(node_offset(node))
    def copy_to_end(node):
        copy(node_end_offset(node))

    def skip(pos):
        nonlocal prev, template
        if pos > prev:
            prev = pos
    def skip_to_start(node):
        skip(node_offset(node))
    def skip_to_end(node):
        skip(node_end_offset(node))

    seen = set()
    def evaluate(node):
        copy_to_end(node)
        if isinstance(node, ast.Constant):
            return
        expr = extract(node)
        if expr in seen:
            return
        seen.add(expr)
        template.append(Evaluate(expr))

    class Collector(ast.NodeVisitor):
        def visit_Subscript(self, node):
            slice = node.slice
            if isinstance(slice, ast.Slice):
                lower = slice.lower
                upper = slice.upper
                step = getattr(slice, 'step')
            else:
                lower = slice
                upper = None
                step = None

            evaluate(lower)
            if upper:
                evaluate(upper)
            if step:
                evaluate(step)

        def visit_Call(self, node):
            copy_to_start(node)
            for i, arg in enumerate(node.args):
                copy_to_start(arg)

                self.visit(arg)
                if node == t:
                    copy_to_end(arg)
                    template.append(Positional(i))
                else:
                    evaluate(arg)
            for i, kw in enumerate(node.keywords):

                if node == t:
                    # Don't show expression for top-level keywords, that's the
                    # whole point of them
                    copy_to_start(kw)
                    template.append(Verbatim(kw.arg))
                    skip_to_end(kw.value)
                    template.append(Keyword(kw.arg))
                else:
                    copy_to_start(kw.value)
                    self.visit(kw.value)
                    evaluate(kw.value)
            copy_to_end(node)

    Collector().visit(t)

    # Replace outer call with whitespace
    template[0] = Verbatim(' ' * (len(name) + 1) + template[0][len(name) + 1:])
    template[-1] = Verbatim(template[-1][:-1])

    # Split/join verbatim strings, such that a string has at most one line break
    # which is at the end
    s = ''
    tmp = []
    def add():
        lines = s.split('\n')
        for line in lines[:-1]:
            tmp.append(Verbatim(line + '\n'))
        if lines[-1]:
            tmp.append(Verbatim(lines[-1]))
    for t in template:
        if isinstance(t, Verbatim):
            s += t
        else:
            add()
            s = ''
            tmp += [t]
    add()
    template = tmp

    # Strip blank lines from beginning/end
    while template and isinstance(template[0], Verbatim) and template[0].isspace():
        template.pop(0)
    while template and isinstance(template[-1], Verbatim) and template[-1].isspace():
        template.pop()

    # Strip trailing whitespace
    if template and isinstance(template[-1], Verbatim):
        template[-1] = Verbatim(template[-1].rstrip())

    # Determine indentation as the longest common whitespace
    indent = float('inf')
    atnl = True
    for t in template:
        if not isinstance(t, Verbatim):
            continue
        if atnl:
            indent = min(indent, indentation(t))
        atnl = t[-1] == '\n'

    # Left adjust according to indentation
    atnl = True
    for i, t in enumerate(template[:]):
        if not isinstance(t, Verbatim):
            continue
        if atnl:
            t = Verbatim(t[indent:])
            template[i] = t
        atnl = t.endswith('\n')

    _cache[key] = template
    return template

def show(*args, **kwargs):
    this = inspect.currentframe()
    call = this.f_back
    lino = call.f_lineno
    path = inspect.getsourcefile(call)

    template = _get(this)

    out = ''
    for t in template:
        if isinstance(t, Verbatim):
            out += t
        else:
            if isinstance(t, Evaluate):
                val = eval(t, call.f_locals, call.f_globals)
            elif isinstance(t, Positional):
                val = args[t]
            elif isinstance(t, Keyword):
                val = kwargs[t]
            val = str(val)
            out += f'\x1b[2m = \x1b[m\x1b[33;1m{val}\x1b[m'

    print(f'\x1b[36m{path}[\x1b[33m{call.f_code.co_name}\x1b[m:\x1b[33m{lino}\x1b[36m]:\x1b[m')
    if template:
        print(out)
