import __builtin__
import dis
import marshal
import pickle
import py_compile
import re
import sys
import time
import fractions
from contextlib import contextmanager

from clojure.lang.cons import Cons
from clojure.lang.cljexceptions import CompilerException, AbstractMethodCall
from clojure.lang.cljkeyword import Keyword
from clojure.lang.ipersistentvector import IPersistentVector
from clojure.lang.ipersistentmap import IPersistentMap
from clojure.lang.ipersistentset import IPersistentSet
from clojure.lang.ipersistentlist import IPersistentList
from clojure.lang.iseq import ISeq
from clojure.lang.lispreader import _AMP_, LINE_KEY, garg
from clojure.lang.namespace import Namespace, findNS, findItem, intern
from clojure.lang.persistentlist import PersistentList, EmptyList
from clojure.lang.persistentvector import PersistentVector
import clojure.lang.rt as RT
from clojure.lang.symbol import Symbol
from clojure.lang.var import Var, threadBindings
from clojure.util.byteplay import *
import clojure.util.byteplay as byteplay
import marshal
import types

_MACRO_ = Keyword("macro")
_NS_ = Symbol("*ns*")
version = (sys.version_info[0] * 10) + sys.version_info[1]

PTR_MODE_GLOBAL = "PTR_MODE_GLOBAL"
PTR_MODE_DEREF = "PTR_MODE_DEREF"

AUDIT_CONSTS = False

class MetaBytecode(object):
    pass


class GlobalPtr(MetaBytecode):
    def __init__(self, ns, name):
        self.ns = ns
        self.name = name

    def __repr__(self):
        return "GblPtr<%s/%s>" % (self.ns.__name__, self.name)

    def emit(self, comp, mode):
        module = self.ns
        val = getattr(module, self.name)

        if isinstance(val, Var):
            if not val.isDynamic():
                val = val.deref()
                return [(LOAD_CONST, val)]
            else:
                if mode is PTR_MODE_DEREF:
                    return [(LOAD_CONST, val),
                            (LOAD_ATTR, "deref"),
                            (CALL_FUNCTION, 0)]
                else:
                    raise CompilerException("Invalid deref mode", mode)

        return [(LOAD_CONST, module),
               (LOAD_ATTR, self.name)]


def expandMetas(bc, comp):
    code = []
    for x in bc:
        if AUDIT_CONSTS and isinstance(x, tuple):
            if x[0] == LOAD_CONST:
                try:
                    marshal.dumps(x[1])
                except:
                    print "Can't marshal", x[1], type(x[1])
                    raise

        if isinstance(x, MetaBytecode):
            code.extend(x.emit(comp, PTR_MODE_DEREF))
        else:
            code.append(x)
    return code


def emitJump(label):
    if version == 26:
        return [(JUMP_IF_FALSE, label),
                (POP_TOP, None)]
    else:
        return [(POP_JUMP_IF_FALSE, label)]


def emitLanding(label):
    if version == 26:
        return [(label, None),
                (POP_TOP, None)]
    else:
        return [(label, None)]


builtins = {}

def register_builtin(sym):
    """A decorator to register a new builtin macro.
    
    Takes the symbol that the macro represents as argument. If the argument is
    a string, it will be converted to a symbol.
    """
    def inner(func):
        builtins[Symbol(sym)] = func
        return func
    return inner


@register_builtin("in-ns")
def compileNS(comp, form):
    rest = form.next()
    if len(rest) != 1:
        raise CompilerException("in-ns only supports one item", rest)
    ns = rest.first()
    code = [(LOAD_CONST, comp),
            (LOAD_ATTR, "setNS")]
    if isinstance(ns, Symbol):
        code.append((LOAD_CONST, ns))
    else:
        code.extend(comp.compile(ns))
    code.append((CALL_FUNCTION, 1))
    set_NS_ = [(LOAD_CONST, comp),
               (LOAD_ATTR, "_NS_"),
               (LOAD_ATTR, "set"),
               (LOAD_CONST, comp),
               (LOAD_ATTR, "ns"),
               (CALL_FUNCTION, 1),
               (LOAD_CONST, comp),
               (LOAD_ATTR, "ns")]
    code.extend(set_NS_)
    return code


@register_builtin("def")
def compileDef(comp, form):
    if len(form) not in [2, 3]:
        raise CompilerException("Only 2 or 3 arguments allowed to def", form)
    sym = form.next().first()
    value = None
    if len(form) == 3:
        value = form.next().next().first()
    if sym.ns is None:
        ns = comp.getNS()
    else:
        ns = sym.ns

    with comp.name(sym):
        code = []
        v = intern(comp.getNS(), sym)

        v.setDynamic(True)
        if len(form) == 3:
            code.append((LOAD_CONST, v))
            code.append((LOAD_ATTR, "bindRoot"))
            compiledValue = comp.compile(value)
            if (isinstance(value, ISeq) and
                value.first().getName() == 'fn' and
                sym.meta() is not None):
                try:
                    compiledValue[0][1].__doc__ = sym.meta()[Keyword('doc')]
                except AttributeError:
                    pass
            code.extend(compiledValue)
            code.append((CALL_FUNCTION, 1))
        else:
            code.append((LOAD_CONST, v))
        v.setMeta(sym.meta())
    return code


def compileBytecode(comp, form):
    codename = form.first().name
    if not hasattr(byteplay, codename):
        raise CompilerException("bytecode {0} unknown".format(codename), form)
    bc = getattr(byteplay, codename)
    hasarg = bc in byteplay.hasarg
    form = form.next()
    arg = None
    if hasarg:
        arg = form.first()
        if not isinstance(arg, (int, str, unicode)) and bc is not LOAD_CONST:
            raise CompilerException(
                "first argument to {0} must be int, unicode, or str".
                format(codename), form)

        arg = evalForm(arg, comp.getNS())
        form = form.next()

    se = byteplay.getse(bc, arg)
    if form != None and se[0] != 0 and (se[0] != len(form) or se[1] > 1):
        raise CompilerException(
            "literal bytecode {0} not supported".format(codename), form)
    s = form
    code = []
    while s is not None:
        code.extend(comp.compile(s.first()))
        s = s.next()
    code.append((bc, arg))
    if se[1] == 0:
        code.append((LOAD_CONST, None))
    return code


@register_builtin("kwapply")
def compileKWApply(comp, form):
    if len(form) < 3:
        raise CompilerException("at least two arguments required to kwapply", form)

    form = form.next()
    fn = form.first()
    form = form.next()
    kws = form.first()
    args = form.next()
    code = []

    s = args
    code.extend(comp.compile(fn))
    while s is not None:
        code.extend(comp.compile(s.first()))
        s = s.next()
    code.extend(comp.compile(kws))
    code.append((LOAD_ATTR, "toDict"))
    code.append((CALL_FUNCTION, 0))
    code.append((CALL_FUNCTION_KW, 0 if args is None else len(args)))
    return code

@register_builtin("loop*")
def compileLoopStar(comp, form):
    if len(form) < 3:
        raise CompilerException("loop* takes at least two args", form)
    form = form.next()
    if not isinstance(form.first(), PersistentVector):
        raise CompilerException(
            "loop* takes a vector as it's first argument", form)
    bindings = RT.seq(form.first())
    args = []
    code = []
    if bindings and len(bindings) % 2:
        raise CompilerException("loop* takes a even number of bindings", form)
    while bindings:
        local, bindings = bindings.first(), bindings.next()
        body, bindings = bindings.first(), bindings.next()
        if not isinstance(local, Symbol) or local.ns is not None:
            raise CompilerException(
                "bindings must be non-namespaced symbols", form)
        code.extend(comp.compile(body))
        alias = RenamedLocal(Symbol("{0}_{1}".format(local, RT.nextID()))
                             if comp.getAlias(local)
                             else local)
        comp.pushAlias(local, alias)
        args.append(local)
        code.extend(alias.compileSet(comp))
    form = form.next()
    recurlabel = Label("recurLabel")
    recur = {"label": recurlabel,
             "args": [comp.getAlias(arg).compileSet(comp) for arg in args]}
    code.append((recurlabel, None))
    with comp.recurPoint(recur):
        code.extend(compileImplcitDo(comp, form))
    comp.popAliases(args)
    return code


@register_builtin("let*")
def compileLetStar(comp, form):
    if len(form) < 2:
        raise CompilerException("let* takes at least two args", form)
    form = form.next()
    if not isinstance(form.first(), IPersistentVector):
        raise CompilerException(
            "let* takes a vector as it's first argument", form)
    bindings = RT.seq(form.first())
    args = []
    code = []
    if bindings and len(bindings) % 2:
        raise CompilerException("let* takes a even number of bindings", form)
    while bindings:
        local, bindings = bindings.first(), bindings.next()
        body, bindings = bindings.first(), bindings.next()
        if not isinstance(local, Symbol) or local.ns is not None:
            raise CompilerException(
                "bindings must be non-namespaced symbols", form)
        code.extend(comp.compile(body))
        alias = RenamedLocal(Symbol("{0}_{1}".format(local, RT.nextID()))
                             if comp.getAlias(local)
                             else local)
        comp.pushAlias(local, alias)
        args.append(local)
        code.extend(alias.compileSet(comp))
    form = form.next()
    code.extend(compileImplcitDo(comp, form))
    comp.popAliases(args)
    return code


@register_builtin(".")
def compileDot(comp, form):
    if len(form) < 3:
        raise CompilerException(
            "Dot form must have at least two arguments", form)
    cls = form.next().first()
    attr = form.next().next().first()
    args = form.next().next().next()
    if isinstance(attr, ISeq):
        if args is not None:
            raise CompilerException("Invalid dot form", form)
        args = attr.next()
        attr = attr.first()
    if not isinstance(attr, Symbol) and attr.ns is None:
        raise CompilerException("Invalid dot form", form)
    if attr.name.startswith("-"):
        # attribute access
        attr = attr.name[1:]
        call = False
    else:
        # method access
        attr = attr.name
        call = True
    code = comp.compile(cls) + [(LOAD_ATTR, attr)]
    if not call:
        if args is not None:
            raise CompilerException(
                "Dot-dash form must have two arguments", form)
    else:
        n_args = len(args or [])
        while args:
            code += comp.compile(args.first())
            args = args.next()
        code += [(CALL_FUNCTION, n_args)]
    return code


@register_builtin("quote")
def compileQuote(comp, form):
    if len(form) != 2:
        raise CompilerException("Quote must only have one argument", form)
    return [(LOAD_CONST, form.next().first())]


@register_builtin("py/if")
def compilePyIf(comp, form):
    if len(form) != 3 and len(form) != 4:
        raise CompilerException("if takes 2 or 3 args", form)
    cmp = comp.compile(form.next().first())
    body = comp.compile(form.next().next().first())
    if len(form) == 3:
        body2 = [(LOAD_CONST, None)]
    else:
        body2 = comp.compile(form.next().next().next().first())

    elseLabel = Label("IfElse")
    endlabel = Label("IfEnd")
    code = cmp
    code.extend(emitJump(elseLabel))
    code.extend(body)
    code.append((JUMP_ABSOLUTE, endlabel))
    code.extend(emitLanding(elseLabel))
    code.extend(body2)
    code.append((endlabel, None))
    return code


@register_builtin("if*")
def compileIfStar(comp, form):
    """
    Compiles the form (if* pred val else?).
    """
    if len(form) != 3 and len(form) != 4:
        raise CompilerException("if takes 2 or 3 args", form)
    cmp = comp.compile(form.next().first())
    body = comp.compile(form.next().next().first())
    if len(form) == 3:
        body2 = [(LOAD_CONST, None)]
    else:
        body2 = comp.compile(form.next().next().next().first())

    elseLabel = Label("IfElse")
    endlabel = Label("IfEnd")
    condition_name = garg(0).name
    code = cmp
    code.append((STORE_FAST, condition_name))
    code.append((LOAD_FAST, condition_name))
    code.append((LOAD_CONST, None))
    code.append((COMPARE_OP, 'is not'))
    code.extend(emitJump(elseLabel))
    code.append((LOAD_FAST, condition_name))
    code.append((LOAD_CONST, False))
    code.append((COMPARE_OP, 'is not'))
    # Use is not instead of != as bool is a subclass of int, and
    # therefore False == 0
    code.extend(emitJump(elseLabel))
    code.extend(body)
    code.append((JUMP_ABSOLUTE, endlabel))
    code.extend(emitLanding(elseLabel))
    code.extend(body2)
    code.append((endlabel, None))
    return code


def unpackArgs(form):
    locals = {}
    args = []
    lastisargs = False
    argsname = None
    for x in form:
        if x == _AMP_:
            lastisargs = True
            continue
        if lastisargs and argsname is not None:
            raise CompilerException(
                "variable length argument must be the last in the function",
                form)
        if lastisargs:
            argsname = x
        if not isinstance(x, Symbol) or x.ns is not None:
            raise CompilerException(
                "fn* arguments must be non namespaced symbols, got {0} instead".
                format(form), form)
        locals[x] = RT.list(x)
        args.append(x.name)
    return locals, args, lastisargs, argsname


@register_builtin("do")
def compileDo(comp, form):
    return compileImplcitDo(comp, form.next())


def compileFn(comp, name, form, orgform):
    locals, args, lastisargs, argsname = unpackArgs(form.first())

    for x in locals:
        comp.pushAlias(x, FnArgument(x))

    if orgform.meta() is not None:
        line = orgform.meta()[LINE_KEY]
    else:
        line = 0
    code = [(SetLineno,line if line is not None else 0)]
    if lastisargs:
        code.extend(cleanRest(argsname.name))

    recurlabel = Label("recurLabel")

    recur = {"label": recurlabel,
    "args": map(lambda x: comp.getAlias(Symbol(x)).compileSet(comp), args)}

    code.append((recurlabel, None))
    with comp.recurPoint(recur):
        code.extend(compileImplcitDo(comp, form.next()))
    code.append((RETURN_VALUE,None))
    comp.popAliases(locals)

    clist = map(lambda x: RT.name(x.sym), comp.closureList())
    code = expandMetas(code, comp)
    c = Code(code, clist, args, lastisargs, False, True,
             str(Symbol(comp.getNS().__name__, name.name)), comp.filename, 0, None)
    if not clist:
        c = types.FunctionType(c.to_code(), comp.ns.__dict__, name.name)

    return [(LOAD_CONST, c)], c


def cleanRest(name):
    label = Label("isclean")
    code = []
    code.append((LOAD_GLOBAL, "len"))
    code.append((LOAD_FAST, name))
    code.append((CALL_FUNCTION, 1))
    code.append((LOAD_CONST, 0))
    code.append((COMPARE_OP, "=="))
    code.extend(emitJump(label))
    code.append((LOAD_CONST, None))
    code.append((STORE_FAST, name))
    if version == 26:
        code.append((LOAD_CONST, None))
    code.extend(emitLanding(label))
    return code


class MultiFn(object):
    def __init__(self, comp, form):
        form = RT.seq(form)
        if len(form) < 1:
            raise CompilerException("FN defs must have at least one arg", form)
        argv = form.first()
        if not isinstance(argv, PersistentVector):
            raise CompilerException("FN arg list must be a vector", form)
        body = form.next()

        self.locals, self.args, self.lastisargs, self.argsname = unpackArgs(argv)
        endLabel = Label("endLabel")
        argcode = [(LOAD_CONST, len),
            (LOAD_FAST, '__argsv__'),
            (CALL_FUNCTION, 1),
            (LOAD_CONST, len(self.args) - (1 if self.lastisargs else 0)),
            (COMPARE_OP, ">=" if self.lastisargs else "==")]
        argcode.extend(emitJump(endLabel))
        for x in range(len(self.args)):
            if self.lastisargs and x == len(self.args) - 1:
                offset = len(self.args) - 1
                argcode.extend([(LOAD_FAST, '__argsv__'),
                    (LOAD_CONST, offset),
                    (SLICE_1, None),
                    (STORE_FAST, self.argsname.name)])
                argcode.extend(cleanRest(self.argsname.name))
            else:
                argcode.extend([(LOAD_FAST, '__argsv__'),
                    (LOAD_CONST, x),
                    (BINARY_SUBSCR, None),
                    (STORE_FAST, self.args[x])])

        for x in self.locals:
            comp.pushAlias(x, FnArgument(x))

        recurlabel = Label("recurLabel")

        recur = {"label": recurlabel,
        "args": map(lambda x: comp.getAlias(Symbol(x)).compileSet(comp), self.args)}

        bodycode = [(recurlabel, None)]
        with comp.recurPoint(recur):
            bodycode.extend(compileImplcitDo(comp, body))
            bodycode.append((RETURN_VALUE, None))
            bodycode.extend(emitLanding(endLabel))
        comp.popAliases(self.locals)

        self.argcode = argcode
        self.bodycode = bodycode


def compileMultiFn(comp, name, form):
    s = form
    argdefs = []

    while s is not None:
        argdefs.append(MultiFn(comp, s.first()))
        s = s.next()
    argdefs = sorted(argdefs, lambda x, y: len(x.args) < len(y.args))
    if len(filter(lambda x: x.lastisargs, argdefs)) > 1:
        raise CompilerException(
            "Only one function overload may have variable number of arguments",
            form)

    code = []
    if len(argdefs) == 1 and not argdefs[0].lastisargs:
        hasvararg = False
        argslist = argdefs[0].args
        code.extend(argdefs[0].bodycode)
    else:
        hasvararg = True
        argslist = ["__argsv__"]
        for x in argdefs:
            code.extend(x.argcode)
            code.extend(x.bodycode)

        code.append((LOAD_CONST, Exception))
        code.append((CALL_FUNCTION, 0))
        code.append((RAISE_VARARGS, 1))

    clist = map(lambda x: RT.name(x.sym), comp.closureList())
    code = expandMetas(code, comp)
    c = Code(code, clist, argslist, hasvararg, False, True, str(Symbol(comp.getNS().__name__, name.name)), comp.filename, 0, None)
    if not clist:
        c = types.FunctionType(c.to_code(), comp.ns.__dict__, name.name)
    return [(LOAD_CONST, c)], c


def compileImplcitDo(comp, form):
    code = []
    s = form
    while s is not None:
        code.extend(comp.compile(s.first()))
        s = s.next()
        if s is not None:
            code.append((POP_TOP, None))
    if not len(code):
        code.append((LOAD_CONST, None))
    return code


@register_builtin("fn*")
def compileFNStar(comp, form):
    aliases = []
    for sym in comp.aliases: # we might have closures to deal with
        comp.pushAlias(sym, Closure(sym))
        aliases.append(sym)

    orgform = form
    if len(form) < 2:
        raise CompilerException("2 or more arguments to fn* required", form)
    form = form.next()
    first = form.first()
    sym = first if isinstance(first, Symbol) else None

    with comp.name(sym):

        if sym:
            form = form.next()
        else:
            sym = Symbol(comp.getNamesString() + "_auto_")

        # This is fun stuff here.  The idea is that we want closures to
        # be able to call themselves.  But we can't get a pointer to a
        # closure until after it's created, which is when we actually
        # run this code.  So, we're going to create a tmp local that
        # is None at first, then pass that in as a possible closure
        # cell.  Then after we create the closure with MAKE_CLOSURE
        # we'll populate this var with the correct value

        selfalias = Closure(sym)
        comp.pushAlias(sym, selfalias)

        # form = ([x] x)
        if isinstance(form.first(), IPersistentVector):
            code, ptr = compileFn(comp, sym, form, orgform)
        # form = (([x] x))
        elif len(form) == 1:
            code, ptr = compileFn(comp, sym, RT.list(*form.first()), orgform)
        # form = (([x] x) ([x y] x))
        else:
            code, ptr = compileMultiFn(comp, sym, form)

    clist = comp.closureList()
    fcode = []

    comp.popAliases(aliases)

    if clist:
        for x in clist:
            if x is not selfalias:   #we'll populate selfalias later
                fcode.extend(comp.getAlias(x.sym).compile(comp))  # Load our local version
                fcode.append((STORE_DEREF, RT.name(x.sym)))            # Store it in a Closure Cell
            fcode.append((LOAD_CLOSURE, RT.name(x.sym)))           # Push the cell on the stack
        fcode.append((BUILD_TUPLE, len(clist)))
        fcode.extend(code)
        fcode.append((MAKE_CLOSURE, 0))
        code = fcode

    if selfalias in clist:
        prefix = []
        prefix.append((LOAD_CONST, None))
        prefix.extend(selfalias.compileSet(comp))
        prefix.extend(code)
        code = prefix
        code.append((DUP_TOP, None))
        code.extend(selfalias.compileSet(comp))

    comp.popAlias(sym) #closure
    return code


def compileVector(comp, form):
    code = []
    code.extend(comp.compile(Symbol("clojure.lang.rt", "vector")))
    for x in form:
        code.extend(comp.compile(x))
    code.append((CALL_FUNCTION, len(form)))
    return code


@register_builtin("recur")
def compileRecur(comp, form):
    s = form.next() or []
    code = []
    if len(s) > len(comp.getRecurPoint()["args"]):
        raise CompilerException("too many arguments to recur", form)
    for recur_val in s:
        code.extend(comp.compile(recur_val))
    sets = comp.getRecurPoint()["args"][:]
    sets.reverse()
    for x in sets:
        code.extend(x)
    code.append((JUMP_ABSOLUTE, comp.getRecurPoint()["label"]))
    return code


@register_builtin("is?")
def compileIs(comp, form):
    if len(form) != 3:
        raise CompilerException("is? requires 2 arguments", form)
    fst = form.next().first()
    itm = form.next().next().first()
    code = comp.compile(fst)
    code.extend(comp.compile(itm))
    code.append((COMPARE_OP, "is"))
    return code


def compileMap(comp, form):
    s = form.seq()
    c = 0
    code = []
    code.extend(comp.compile(Symbol("clojure.lang.rt", "map")))
    while s is not None:
        kvp = s.first()
        code.extend(comp.compile(kvp.getKey()))
        code.extend(comp.compile(kvp.getValue()))
        c += 2
        s = s.next()
    code.append([CALL_FUNCTION, c])
    return code


def compileKeyword(comp, kw):
    return [(LOAD_CONST, kw)]


def compileBool(comp, b):
    return [(LOAD_CONST, b)]


@register_builtin("throw")
def compileThrow(comp, form):
    if len(form) != 2:
        raise CompilerException("throw requires two arguments", form)
    code = comp.compile(form.next().first())
    code.append((RAISE_VARARGS, 1))
    return code


@register_builtin("applyTo")
def compileApply(comp, form):
    s = form.next()
    code = []
    while s is not None:
        code.extend(comp.compile(s.first()))

        s = s.next()
    code.append((LOAD_CONST, RT.seqToTuple))
    code.append((ROT_TWO, None))
    code.append((CALL_FUNCTION, 1))
    code.append((CALL_FUNCTION_VAR, 0))
    return code


def compileBuiltin(comp, form):
    if len(form) != 2:
        raise CompilerException("throw requires two arguments", form)
    name = str(form.next().first())
    return [(LOAD_CONST, getBuiltin(name))]


def getBuiltin(name):
    if hasattr(__builtin__, name):
        return getattr(__builtin__, name)
    raise CompilerException("Python builtin {0} not found".format(name), name)


@register_builtin("let-macro")
def compileLetMacro(comp, form):
    if len(form) < 3:
        raise CompilerException(
            "alias-properties takes at least two args", form)
    form = form.next()
    s = RT.seq(form.first())
    syms = []
    while s is not None:
        sym = s.first()
        syms.append(sym)
        s = s.next()
        if s is None:
            raise CompilerException(
                "let-macro takes a even number of bindings", form)
        macro = s.first()
        comp.pushAlias(sym, LocalMacro(sym, macro))
        s = s.next()
    body = form.next()
    code = compileImplcitDo(comp, body)
    comp.popAliases(syms)
    return code


@register_builtin("__compiler__")
def compileCompiler(comp, form):
    return [(LOAD_CONST, comp)]


@register_builtin("try")
def compileTry(comp, form):
    """
    Compiles the try macro.
    """
    assert form.first() == Symbol("try")
    form = form.next()

    if not form:
        # I don't like this, but (try) == nil
        return [(LOAD_CONST, None)]

    # Keep a list of compiled might-throw statements in
    # implicit-do try body
    body = comp.compile(form.first())
    form = form.next()

    if not form:
        # If there are no further body statements, or
        # catch/finally/else etc statements, just
        # compile the body
        return body

    catch = []
    els = None
    fin = None
    for subform in form:
        try:
            name = subform.first()
        except AttributeError:
            name = None
        if name in (Symbol("catch"), Symbol("except")):
            name = subform.first()
            if len(subform) != 4:
                raise CompilerException(
                    "try {0} blocks must be 4 items long".format(name), form)

            # Exception is second, val is third
            exception = subform.next().first()
            if not isinstance(exception, Symbol):
                raise CompilerException(
                    "exception passed to {0} block must be a symbol".
                    format(name), form)
            for ex, _, _ in catch:
                if ex == exception:
                    raise CompilerException(
                        "try cannot catch duplicate exceptions", form)

            var = subform.next().next().first()
            if not isinstance(var, Symbol):
                raise CompilerException(
                    "variable name for {0} block must be a symbol".
                    format(name), form)
            val = subform.next().next().next().first()
            catch.append((exception, var, val))
        elif name == Symbol("else"):
            if len(subform) != 2:
                raise CompilerException(
                    "try else blocks must be 2 items", form)
            elif els:
                raise CompilerException(
                    "try cannot have multiple els blocks", form)
            els = subform.next().first()
        elif name == Symbol("finally"):
            if len(subform) != 2:
                raise CompilerException(
                    "try finally blocks must be 2 items", form)
            elif fin:
                raise CompilerException(
                    "try cannot have multiple finally blocks", form)
            fin = subform.next().first()
        else:
            # Append to implicit do
            body.append((POP_TOP, None))
            body.extend(comp.compile(subform))

    if fin and not catch and not els:
        return compileTryFinally(body, comp.compile(fin))
    elif catch and not fin and not els:
        return compileTryCatch(comp, body, catch)
    elif not fin and not catch and els:
        raise CompilerException(
            "try does not accept else statements on their own", form)

    if fin and catch and not els:
        return compileTryCatchFinally(comp, body, catch,
                                      comp.compile(fin))

    if not fin and not catch and not els:
        # No other statements, return compiled body
        return body

def compileTryFinally(body, fin):
    """
    Compiles the try/finally form. Takes the body of the try statement, and the
    finally statement. They must be compiled bytecode (i.e. comp.compile(body)).
    """
    finallyLabel = Label("TryFinally")

    ret_val = "__ret_val_{0}".format(RT.nextID())

    code = [(SETUP_FINALLY, finallyLabel)]
    code.extend(body)
    code.append((STORE_FAST, ret_val))
    code.append((POP_BLOCK, None))
    code.append((LOAD_CONST, None))
    code.append((finallyLabel, None))
    code.extend(fin)
    code.extend([(POP_TOP, None),
                 (END_FINALLY, None),
                 (LOAD_FAST, ret_val)])
    return code


def compileTryCatch(comp, body, catches):
    """
    Compiles the try/catch/catch... form. Takes the body of the try statement,
    and a list of (exception, exception_var, except_body) tuples for each
    exception. The order of the list is important.
    """
    assert len(catches), "Calling compileTryCatch with empty catches list"

    catch_labels = [Label("TryCatch_{0}".format(ex)) for ex, _, _ in catches]
    endLabel = Label("TryCatchEnd")
    endFinallyLabel = Label("TryCatchEndFinally")
    firstExceptLabel = Label("TryFirstExcept")

    ret_val = "__ret_val_{0}".format(RT.nextID())

    code = [(SETUP_EXCEPT, firstExceptLabel)] # First catch label
    code.extend(body)
    code.append((STORE_FAST, ret_val)) # Because I give up with
    # keeping track of what's in the stack
    code.append((POP_BLOCK, None))
    code.append((JUMP_FORWARD, endLabel)) # if all went fine, goto end

    n = len(catches)
    for i, (exception, var, val) in enumerate(catches):

        comp.pushAlias(var, FnArgument(var)) # FnArgument will do

        last = i == n - 1

        # except Exception
        code.extend(emitLanding(catch_labels[i]))
        if i == 0:
            # first time only
            code.append((firstExceptLabel, None))
        code.append((DUP_TOP, None))
        code.extend(comp.compile(exception))
        code.append((COMPARE_OP, "exception match"))
        code.extend(emitJump(catch_labels[i + 1] if not last else
                             endFinallyLabel))

        # as e
        code.append((POP_TOP, None))
        code.append((STORE_FAST, var.name))
        code.append((POP_TOP, None))

        # body
        code.extend(comp.compile(val))
        code.append((STORE_FAST, ret_val))
        code.append((JUMP_FORWARD, endLabel))

        comp.popAlias(var)

    code.extend(emitLanding(endFinallyLabel))
    code.append((END_FINALLY, None))
    code.append((endLabel, None))
    code.append((LOAD_FAST, ret_val))

    return code

def compileTryCatchFinally(comp, body, catches, fin):
    """
    Compiles the try/catch/finally form.
    """
    assert len(catches), "Calling compileTryCatch with empty catches list"

    catch_labels = [Label("TryCatch_{0}".format(ex)) for ex, _, _ in catches]
    finallyLabel = Label("TryCatchFinally")
    notCaughtLabel = Label("TryCatchFinally2")
    firstExceptLabel = Label("TryFirstExcept")
    normalEndLabel = Label("NoExceptionLabel")

    ret_val = "__ret_val_{0}".format(RT.nextID())

    code = [
        (SETUP_FINALLY, finallyLabel),
        (SETUP_EXCEPT, firstExceptLabel)] # First catch label
    code.extend(body)
    code.append((STORE_FAST, ret_val)) # Because I give up with
    # keeping track of what's in the stack
    code.append((POP_BLOCK, None))
    code.append((JUMP_FORWARD, normalEndLabel))
    # if all went fine, goto finally

    n = len(catches)
    for i, (exception, var, val) in enumerate(catches):

        comp.pushAlias(var, FnArgument(var)) # FnArgument will do

        last = i == n - 1
        first = i == 0

        # except Exception
        code.extend(emitLanding(catch_labels[i]))
        if first:
            # After the emitLanding, so as to split the label
            code.append((firstExceptLabel, None))
        code.append((DUP_TOP, None))
        code.extend(comp.compile(exception))
        code.append((COMPARE_OP, "exception match"))
        code.extend(emitJump(catch_labels[i + 1] if not last
                             else notCaughtLabel))

        # as e
        code.append((POP_TOP, None))
        code.append((STORE_FAST, var.name))
        code.append((POP_TOP, None))

        # body
        code.extend(comp.compile(val))
        code.append((STORE_FAST, ret_val))
        code.append((JUMP_FORWARD, normalEndLabel))

        comp.popAlias(var)

    code.extend(emitLanding(notCaughtLabel))
    code.append((END_FINALLY, None))
    code.append((normalEndLabel, None))
    code.append((POP_BLOCK, None))
    code.append((LOAD_CONST, None))

    code.append((finallyLabel, None))
    code.extend(fin)
    code.append((POP_TOP, None))
    code.append((END_FINALLY, None))
    code.append((LOAD_FAST, ret_val))

    return code


# We should mention a few words about aliases.  Aliases are created when
# the user uses closures, fns, loop, let, or let-macro.  For some forms
# like let or loop, the alias just creates a new local variable in which
# to store the data.  In other cases, closures are created.  To handle
# all these cases, we store aliases on stacks.  This will allow us to
# override what certain symbols resolve to.
#
# For instance:
#
# (fn bar [a b]
#    (let [b (inc b)
#          z 1]
#        (let-macro [a (fn [fdecl& env& decl] 'z)]
#            (let [o (fn [a] a)]
#                 [a (o b)]))))
#
# As each new local is created, it is pushed onto the stack, then only
# the top most local is executed whenever a new local is resolved.  This
# allows the above example to resolve exactly as desired. lets will
# never stop on top of each other, let-macros can turn 'x into (.-x
# self), etc.

class Alias(object):
    """Base class for all aliases"""

    def compile(self, comp):
        raise AbstractMethodCall(self)

    def compileSet(self, comp):
        raise AbstractMethodCall(self)


class FnArgument(Alias):
    """An alias provided by the arguments to a fn* in the fragment (fn
    [a] a) a is a FnArgument"""

    def __init__(self, sym):
        self.sym = sym

    def compile(self, comp):
        return [(LOAD_FAST, RT.name(self.sym))]

    def compileSet(self, comp):
        return [(STORE_FAST, RT.name(self.sym))]


class RenamedLocal(Alias):
    """An alias created by a let, loop, etc."""

    def __init__(self, sym):
        self.sym = sym
        self.newsym = Symbol(RT.name(sym) + str(RT.nextID()))

    def compile(self, comp):
        return [(LOAD_FAST, RT.name(self.newsym))]

    def compileSet(self, comp):
        return [(STORE_FAST, RT.name(self.newsym))]


class Closure(Alias):
    """Represents a value that is contained in a closure"""

    def __init__(self, sym):
        self.sym = sym
        self.isused = False  ## will be set to true whenever this is compiled

    def isUsed(self):
        return self.isused

    def compile(self, comp):
        self.isused = True
        return [(LOAD_DEREF, RT.name(self.sym))]

    def compileSet(self, comp):
        return [(STORE_DEREF, RT.name(self.sym))]


class LocalMacro(Alias):
    """represents a value that represents a local macro"""

    def __init__(self, sym, macroform):
        self.sym = sym
        self.macroform = macroform

    def compile(self, comp):
        code = comp.compile(self.macroform)
        return code


class SelfReference(Alias):
    def __init__(self, var):
        self.var = var
        self.isused = False

    def compile(self, comp):
        self.isused = True
        return [(LOAD_CONST, self.var),
                (LOAD_ATTR, "deref"),
                (CALL_FUNCTION, 0)]


class Name(object):
    """Slot for a name"""
    def __init__(self, name):
        self.name = name
        self.isused = False


def evalForm(form, ns):
    comp = Compiler()
    code = comp.compile(form)
    code = expandMetas(code, comp)
    return comp.executeCode(code, ns)


def ismacro(macro):
    return (not isinstance(macro, type)
            and (hasattr(macro, "meta")
            and macro.meta()
            and macro.meta()[_MACRO_])
            or getattr(macro, "macro?", False))


def meta(form):
    return getattr(form, "meta", lambda: None)()


def macroexpand(form, comp, one=False):
    first = form.first()
    if isinstance(first, Symbol):
        if first.ns == 'py' or first.ns == "py.bytecode":
            return form, False

        if (first.ns is None and
            first.name.startswith(".") and first.name != "."):
            form = RT.list(Symbol("."), form.next().first(),
                           Symbol(first.name[1:]), *(form.next().next() or ()))
            return comp.compile(form), True

        itm = findItem(comp.getNS(), first)
        dreffed = itm
        if isinstance(dreffed, Var):
            dreffed = itm.deref()

        # Handle macros here
        # TODO: Break this out into a seperate function
        if ismacro(itm) or ismacro(dreffed):
            macro = dreffed
            args = RT.seqToTuple(form.next())

            macroform = getattr(macro, "_macro-form", macro)

            mresult = macro(macroform, None, *args)

            if hasattr(mresult, "withMeta") and hasattr(form, "meta"):
                mresult = mresult.withMeta(form.meta())
            if not one:
                mresult = comp.compile(mresult)
            return mresult, True

    return form, False


class Compiler(object):
    def __init__(self):
        self.aliases = {}
        self._recurPoints = []
        self._names = []
        self.ns = clojure_core = Namespace("clojure.core")
        self.lastlineno = -1
        self.filename = "<unknown>"
        self._NS_ = findItem(clojure_core, _NS_)

    def setFile(self, filename):
        self.filename = filename

    def pushAlias(self, sym, alias):
        self.aliases.setdefault(sym, []).append(alias)

    def getAlias(self, sym):
        return self.aliases.get(sym, [None])[-1]

    def popAlias(self, sym):
        self.aliases[sym].pop()
        if not self.aliases[sym]:
            self.aliases.pop(sym)

    def popAliases(self, syms):
        for sym in syms:
            self.popAlias(sym)

    @contextmanager
    def recurPoint(self, label):
        """Temporarily set the target of recur calls to a label.
        """
        self._recurPoints.append(label)
        yield
        self._recurPoints.pop()

    def getRecurPoint(self):
        return self._recurPoints[-1]

    @contextmanager
    def name(self, sym=None):
        """Temporarily add a symbol's name to the name stack, if not None.
        """
        if sym is not None:
            self._names.append(Name(sym.name))
            yield
            self._names.pop()
        else:
            yield

    def getNamesString(self, markused=True):
        if not self._names:
            return "fn_{0}".format(RT.nextID())
        s = "_".join(r.name for r in self._names)
        if self._names[-1].isused:
            s += str(RT.nextID())
        if markused:
            self._names[-1].isused = True
        return s

    def compileForm(self, form):
        if form.first() in builtins:
            return builtins[form.first()](self, form)
        form, ret = macroexpand(form, self)
        if ret:
            return form
        if isinstance(form.first(), Symbol):
            if form.first().ns == "py.bytecode":
                return compileBytecode(self, form)
            if form.first().name.startswith(".-"):
                return self.compilePropertyAccess(form)
            if form.first().name.startswith(".") and form.first().ns is None:
                return self.compileMethodAccess(form)
        c = self.compile(form.first())
        f = form.next()
        acount = 0
        while f is not None:
            c.extend(self.compile(f.first()))
            acount += 1
            f = f.next()
        c.append((CALL_FUNCTION, acount))

        return c

    def compileAccessList(self, sym):
        if sym.ns == 'py':
            return [(LOAD_CONST, getBuiltin(RT.name(sym)))]

        code = self.getAccessCode(sym)
        return code

    def getAccessCode(self, sym):
        if sym.ns is None or sym.ns == self.getNS().__name__:
            if self.getNS() is None:
                raise CompilerException("no namespace has been defined", None)
            if not hasattr(self.getNS(), RT.name(sym)):
                raise CompilerException(
                    "could not resolve '{0}', '{1}' not found in {2} reference {3}".
                    format(sym, RT.name(sym), self.getNS().__name__,
                           self.getNamesString(False)),
                    None)
            var = getattr(self.getNS(), RT.name(sym))
            return [GlobalPtr(self.getNS(), RT.name(sym))]

        if Symbol(sym.ns) in getattr(self.getNS(), "__aliases__", {}):
            sym = Symbol(self.getNS().__aliases__[Symbol(sym.ns)].__name__, RT.name(sym))

        splt = []
        if sym.ns is not None:
            module = findNS(sym.ns)
            if not hasattr(module, RT.name(sym)):
                raise CompilerException(
                    "{0} does not define {1}".format(module, RT.name(sym)),
                    None)
            return [GlobalPtr(module, RT.name(sym))]

        code = LOAD_ATTR if sym.ns else LOAD_GLOBAL
        #if not sym.ns and RT.name(sym).find(".") != -1 and RT.name(sym) != "..":
        raise CompilerException(
            "unqualified dotted forms not supported: {0}".format(sym), sym)

        if len(RT.name(sym).replace(".", "")):
            splt.extend((code, attr) for attr in RT.name(sym).split("."))
        else:
            splt.append((code, RT.name(sym)))
        return splt

    def compileSymbol(self, sym):
        """ Compiles the symbol. First the compiler tries to compile it
            as an alias, then as a global """
        if self.getAlias(sym):
            return self.compileAlias(sym)
        return self.compileAccessList(sym)

    def compileAlias(self, sym):
        """ Compiles the given symbol as an alias."""
        alias = self.getAlias(sym)
        if alias is None:
            raise CompilerException("Unknown Local {0}".format(sym), None)
        return alias.compile(self)

    def closureList(self):
        closures = []
        for sym in self.aliases:
            alias = self.getAlias(sym)
            if isinstance(alias, Closure) and alias.isUsed():
                closures.append(alias)
        return closures

    def compile(self, itm):
        try:
            c = []
            lineset = False
            if getattr(itm, "meta", lambda: None)() is not None:
                line = itm.meta()[LINE_KEY]
                if line is not None and line > self.lastlineno:
                    lineset = True
                    self.lastlineno = line
                    c.append([SetLineno, line])

            if isinstance(itm, Symbol):
                c.extend(self.compileSymbol(itm))
            elif isinstance(itm, PersistentList) or isinstance(itm, Cons):
                c.extend(self.compileForm(itm))
            elif itm is None:
                c.extend(self.compileNone(itm))
            elif type(itm) in [str, int, types.ClassType, type, Var]:
                c.extend([(LOAD_CONST, itm)])
            elif isinstance(itm, IPersistentVector):
                c.extend(compileVector(self, itm))
            elif isinstance(itm, IPersistentMap):
                c.extend(compileMap(self, itm))
            elif isinstance(itm, Keyword):
                c.extend(compileKeyword(self, itm))
            elif isinstance(itm, bool):
                c.extend(compileBool(self, itm))
            elif isinstance(itm, EmptyList):
                c.append((LOAD_CONST, itm))
            elif isinstance(itm, unicode):
                c.append((LOAD_CONST, itm))
            elif isinstance(itm, float):
                c.append((LOAD_CONST, itm))
            elif isinstance(itm, long):
                c.append((LOAD_CONST, itm))
            elif isinstance(itm, fractions.Fraction):
                c.append((LOAD_CONST, itm))
            elif isinstance(itm, IPersistentSet):
                c.append((LOAD_CONST, itm))
            elif isinstance(itm, type(re.compile(""))):
                c.append((LOAD_CONST, itm))
            else:
                raise CompilerException(
                    " don't know how to compile {0}".format(type(itm)), None)

            if len(c) < 2 and lineset:
                return []
            return c
        except:
            print "Compiling {0}".format(itm)
            raise

    def compileNone(self, itm):
        return [(LOAD_CONST, None)]

    def setNS(self, ns):
        self.ns = Namespace(ns)

    def getNS(self):
        return self.ns

    def executeCode(self, code, ns=None):
        ns = ns or self.getNS()
        if code == []:
            return None
        newcode = expandMetas(code, self)
        newcode.append((RETURN_VALUE, None))
        c = Code(newcode, [], [], False, False, False,
                 str(Symbol(ns.__name__, "<string>")), self.filename, 0, None)
        try:
            c = c.to_code()
        except:
            for x in newcode:
                print x
            raise

        # work on .cljs
        #from clojure.util.freeze import write, read
        #with open("foo.cljs", "wb") as fl:
        #    f = write(c, fl)

        with threadBindings({self._NS_: ns}):
            retval = eval(c, ns.__dict__)
        return retval

    def standardImports(self):
        return [(LOAD_CONST, -1),
            (LOAD_CONST, None),
            (IMPORT_NAME, "clojure.standardimports"),
            (IMPORT_STAR, None)]

    def executeModule(self, code):
        code.append((RETURN_VALUE, None))
        c = Code(code, [], [], False, False, False,
                 str(Symbol(self.getNS().__name__, "<string>")), self.filename, 0, None)

        dis.dis(c)
        codeobject = c.to_code()

        with open('output.pyc', 'wb') as fc:
            fc.write(py_compile.MAGIC)
            py_compile.wr_long(fc, long(time.time()))
            marshal.dump(c, fc)
