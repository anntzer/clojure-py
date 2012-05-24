# -*- coding: utf-8 -*-

import fractions
import re
import string
import unicodedata

from clojure.lang.cljexceptions import ReaderException, IllegalStateException
from clojure.lang.cljkeyword import Keyword, TAG_KEY, T, LINE_KEY
from clojure.lang.fileseq import StringReader
from clojure.lang.globals import currentCompiler
from clojure.lang.ipersistentlist import IPersistentList
from clojure.lang.ipersistentvector import IPersistentVector
from clojure.lang.ipersistentmap import IPersistentMap
from clojure.lang.ipersistentset import IPersistentSet
from clojure.lang.ipersistentcollection import IPersistentCollection
from clojure.lang.persistenthashmap import EMPTY as EMPTY_MAP
from clojure.lang.persistentvector import EMPTY as EMPTY_VECTOR
from clojure.lang.persistenthashset import createWithCheck
import clojure.lang.rt as RT
from clojure.lang.symbol import Symbol
from clojure.lang.var import Var, threadBindings
import clojure.lang.namespace as namespace
from ..protocols import ISeq

_AMP_ = Symbol("&")
_FN_ = Symbol("fn")
_VAR_ = Symbol("var")
_APPLY_ = Symbol("apply")
_DEREF_ = Symbol("deref")
_QUOTE_ = Symbol("quote")
_SYNTAX_QUOTE_ = Symbol("`")
_UNQUOTE_ = Symbol("~")
_UNQUOTE_SPLICING_ = Symbol("~@")

ARG_ENV = Var(None).setDynamic()
GENSYM_ENV = Var(None).setDynamic()

symbolPat = re.compile("[:]?([\\D^/].*/)?([\\D^/][^/]*)")

intPat = re.compile(r"""
(?P<sign>[+-])?
  (:?
    # radix: 12rAA
    (?P<radix>(?P<base>[1-9]\d?)[rR](?P<value>[0-9a-zA-Z]+))    |
    # decima1: 0, 23, 234, 3453455
    (?P<decInt>0|[1-9]\d*)                                      |
    # octal: 0777
    0(?P<octInt>[0-7]+)                                         |
    # hex: 0xff
    0[xX](?P<hexInt>[0-9a-fA-F]+))
$                               # ensure the entire string matched
""", re.X)

# This floating point re has to be a bit more accurate than the original
# Clojure version because Clojure uses Double.parseDouble() to convert the
# string to a floating point value for return. If it can't convert it (for
# what ever reason), it throws.  Python float() is a lot more liberal. It's
# not a parser:
#
# >>> float("08") => 8.0
#
# I could just check for a decimal in matchNumber(), but is that the *only*
# case I need to check? I think it best to fully define a valid float in the
# re.
floatPat = re.compile(r"""
[+-]?
\d+
(\.\d*([eE][+-]?\d+)? |
 [eE][+-]?\d+)
$                               # ensure the entire string matched
""", re.X)

# Clojure allows what *should* be octal numbers as the numerator and
# denominator. But they are parsed as base 10 integers that allow leading
# zeros. In my opinion this isn't consistent behavior at all.
# The following re only allows base 10 integers.
ratioPat = re.compile("[-+]?(0|[1-9]\d*)/(0|[1-9]\d*)$")

# clojure-py constants
# for interpretToken()
INTERPRET_TOKENS = {"nil": None,
                    "true": True,
                    "false": False,
                    }

# for stringReader()
chrLiterals = {'t': '\t',
               'r': '\r',
               'n': '\n',
               'b': '\b',
               '\\': '\\',
               '"': '"',
               "f": '\f',
               }

# for regexReader()
# http://docs.python.org/reference/lexical_analysis.html
regexCharLiterals = {'\\': '\\',
                    "'": "\'",
                    '"': '"',
                    'a': '\a',
                    'b': '\b',
                    "f": '\f',
                    'n': '\n',
                    'r': '\r',
                    't': '\t',
                    'v': '\v',
                    }

# for characterReader()
namedChars = {"newline": "\n",
              "space": " ",
              "tab": "\t",
              "backspace": "\b",
              "formfeed": "\f",
              "return": "\r",
              }

whiteSpace = set(",\n\t\r\b\f ")
octalChars = set("01234567")
commentTerminators = set(['', '\n', '\r'])
# legal characters between the braces: "\N{...}" for readNamedUnicodeChar()
unicodeNameChars = set(string.letters + "- ")
hexChars = set("0123456789abcdefABCDEF")


def read1(rdr):
    rdr.next()
    if rdr is None:
        return ""
    ch = rdr.first()
    import inspect
    return ch


def isMacro(c):
    return c in macros


def isTerminatingMacro(ch):
    return ch != "#" and ch != "\'" and isMacro(ch)


def readString(s):
    "Return the first object found in s"
    r = StringReader(s)
    return read(r, False, None, False)


def read(rdr, eofIsError, eofValue, isRecursive):
    """Read and return one object from rdr.

    rdr -- a read/unread-able object
    eofIsError -- if True, raise an exception when rdr is out of characters
                  if False, return eofValue instead
    eofValue --   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    isRecursive -- not currently used

    The basic sequence is as follows:
    1. consume white space
    2. check for eof
    3. check for a number (sans [+-])       <- Does this
    4. dispatch on macro characters         <- order matter?
    5. check for a number (with [+-])
    6. check for a symbol"""
    while True:
        ch = read1(rdr)

        while ch in whiteSpace:
            ch = read1(rdr)

        if ch == "":
            if eofIsError:
                raise ReaderException("EOF while reading", rdr)
            else:
                return eofValue

        if ch.isdigit():
            return readNumber(rdr, ch)

        m = getMacro(ch)
        if m is not None:
            ret = m(rdr, ch)
            if ret is rdr:
                continue
            return ret

        if ch in ["+", "-"]:
            ch2 = read1(rdr)
            if ch2.isdigit():
                rdr.back()
                n = readNumber(rdr, ch)
                return n
            rdr.back()

        token = readToken(rdr, ch)
        return interpretToken(token)


def unquoteReader(rdr, tilde):
    """Return one of:
    * (unquote-splicing next-object-read)
    * (unquote next-object-read)"""
    s = read1(rdr)
    if s == "":
        raise ReaderException("EOF reading unquote", rdr)
    if s == "@":
        o = read(rdr, True, None, True)
        return RT.list(_UNQUOTE_SPLICING_, o)
    else:
        rdr.back()
        o = read(rdr, True, None, True)
        return RT.list(_UNQUOTE_, o)


# replaces the overloaded readUnicodeChar()
# Not really cemented to the reader
def stringCodepointToUnicodeChar(token, offset, length, base):
    """Return a unicode character given a string that specifies a codepoint.

    token -- string to parse
    offset -- index into token where codepoint starts
    length -- maximum number of digits to read from offset
    base -- expected radix of the codepoint

    Return a unicode string of length one."""
    if len(token) != offset + length:
        raise UnicodeError("Invalid unicode character: \\{0}".format(token))
    try:
        return unichr(int(token[offset:], base))
    except:
        raise UnicodeError("Invalid unicode character: \\{0}".format(token))


def readUnicodeChar(rdr, initch, base, length, exact):
    """Read a string that specifies a Unicode codepoint.

    rdr -- read/unread-able object
    initch -- the first character of the codepoint string
    base -- expected radix of the codepoint
    length -- maximum number of characters in the codepoint
    exact -- if True, codepoint string must contain length characters
             if False, it must contain [1, length], inclusive

    May raise ReaderException. Return a unicode string of length one."""
    digits = []
    try:
        int(initch, base)
        digits.append(initch)
    except ValueError:
        raise ReaderException("Expected base {0} digit, got:"
                              " ({1})".format(base, initch or "EOF"), rdr)
    for i in range(2, length+1):
        ch = read1(rdr)
        if ch == "" or ch in whiteSpace or isMacro(ch):
            rdr.back()
            i -= 1
            break
        try:
            int(ch, base)
            digits.append(ch)
        except ValueError:
            if exact:
                raise ReaderException("Expected base {0} digit, got:"
                                      " ({1})".format(base, ch or "EOF"), rdr)
            else:
                rdr.back()
                break
    if i != length and exact:
        raise ReaderException("Invalid character length: ({0}), should be:"
                              " ({1})".format(i, length), rdr)
    return unichr(int("".join(digits), base))


def characterReader(rdr, backslash):
    """Read a single clojure-py formatted character from rdr.

    rdr -- read/unread-able object
    backslash -- ignored

    May raise ReaderException. Return a unicode string of lenght one."""
    ch = rdr.read()
    if ch == "":
        raise ReaderException("EOF while reading character", rdr)
    token = readToken(rdr, ch)  # .decode("utf-8")
    if len(token) == 1:
        return token
    elif token in namedChars:
        return namedChars[token]
    elif token.startswith("u"):
        try:
            ch = stringCodepointToUnicodeChar(token, 1, 4, 16)
        except UnicodeError as e:
            raise ReaderException(e.args[0], rdr)
        codepoint = ord(ch)
        if u"\ud800" <= ch <= u"\udfff":
            raise ReaderException("Invalid character constant in literal"
                                  " string: \\{0}".format(token), rdr)
        return ch
    elif token.startswith("o"):
        if len(token) > 4:
            raise ReaderException("Invalid octal escape sequence length in"
                                  " literal string. Three digits max:"
                                  " \\{0}".format(token), rdr)
        try:
            ch = stringCodepointToUnicodeChar(token, 1, len(token) - 1, 8)
        except UnicodeError as e:
            raise ReaderException(e.args[0], rdr)
        codepoint = ord(ch)
        if codepoint > 255:
            raise ReaderException("Octal escape sequence in literal string"
                                  " must be in range [0, 377], got:"
                                  " (\\o{0})".format(codepoint), rdr)
        return ch
    raise ReaderException("Unsupported character: \\" + token, rdr)


def stringReader(rdr, doublequote):
    """Read a double-quoted "foo" literal string from rdr.

    rdr -- a read/unread-able object
    doublequote -- ignored

    May raise ReaderException. Return a str or unicode object."""
    buf = []
    ch = read1(rdr)
    while True:
        if ch == "":
            raise ReaderException("EOF while reading string")
        if ch == '\\':
            ch = read1(rdr)
            if ch == "":
                raise ReaderException("EOF while reading string")
            elif ch in chrLiterals:
                ch = chrLiterals[ch]
            elif ch == "u":
                ch = read1(rdr)
                if not ch in hexChars:
                    raise ReaderException("Hexidecimal digit expected after"
                                          " \\u in literal string, got:"
                                          " ({0})".format(ch), rdr)
                ch = readUnicodeChar(rdr, ch, 16, 4, True)
            elif ch in octalChars:
                ch = readUnicodeChar(rdr, ch, 8, 3, False)
                if ord(ch) > 255:
                    raise ReaderException("Octal escape sequence in literal"
                                          " string must be in range [0, 377]"
                                          ", got: ({0})".format(ord(ch)),
                                          rdr)
            else:
                raise ReaderException("Unsupported escape character in"
                                      " literal string: \\{0}".format(ch), rdr)
        elif ch == '"':
            return "".join(buf)
        buf += ch
        ch = read1(rdr)


def readToken(rdr, initch):
    """Read and return the next valid token from rdr.

    rdr -- read/unread-able object
    initch -- first character of returned token

    Collect characters until the eof is reached, white space is read, or a
    terminating macro character is read."""
    sb = [initch]
    while True:
        ch = read1(rdr)
        if ch == "" or ch in whiteSpace or isTerminatingMacro(ch):
            rdr.back()
            break
        sb.append(ch)
    s = "".join(sb)
    return s


def interpretToken(s):
    """Return the value defined by the string s.

    This function exists as a pre-filter to matchSymbol(). If is is found in
    lispreader.INTERPRET_TOKENS, return that, else see if s is a valid Symbol
    and return that.

    Raise ReaderException if s is not a valid token."""
    if s in INTERPRET_TOKENS:
        return INTERPRET_TOKENS[s]
    ret = matchSymbol(s)
    if ret is None:
        raise ReaderException("Unknown symbol {0}".format(s))
    return ret


def readNumber(rdr, initch):
    """Return the next number read from rdr.

    rdr -- a read/unread-able object
    initch -- the first character of the number

    May raise ReaderException."""
    sb = [initch]
    while True:
        ch = read1(rdr)
        if ch == "" or ch in whiteSpace or isMacro(ch):
            rdr.back()
            break
        sb.append(ch)

    s = "".join(sb)
    try:
        n = matchNumber(s)
    except Exception as e:
        raise ReaderException(e.args[0], rdr)
    if n is None:
        raise ReaderException("Invalid number: " + s, rdr)
    return n


def matchNumber(s):
    """Find if the string s is a valid literal number.

    Return the numeric value of s if so, else return None."""
    mo = intPat.match(s)
    if mo:
        mogd = mo.groupdict()
        sign = mogd["sign"] or "+"
        # 12rAA
        if mogd["radix"]:
            return int(sign + mogd["value"], int(mogd["base"], 10))
        # 232
        elif mogd["decInt"]:
            return int(sign + mogd["decInt"])
        # 0777
        elif mogd["octInt"]:
            return int(sign + mogd["octInt"], 8)
        # 0xdeadbeef
        elif mogd["hexInt"]:
            return int(sign + mogd["hexInt"], 16)
    # 1e3, 0.3,
    mo = floatPat.match(s)
    if mo:
        return float(mo.group())
    # 1/2
    mo = ratioPat.match(s)
    if mo:
        return fractions.Fraction(mo.group())
    # no match
    return None


def getMacro(ch):
    """Return the function associated with the macro character ch"""
    return macros.get(ch)       # None if key not present


def commentReader(rdr, semicolon):
    """Read and discard characters until a newline or eof is reached.

    rdr -- read/unread-able object
    semicolon -- ignored

    Return rdr"""
    while True:
        ch = read1(rdr)
        if ch in commentTerminators:
            break
    return rdr


def discardReader(rdr, underscore):
    """Read and discard the next object from rdr.

    rdr -- read/unread-able object
    underscore -- ignored

    Return rdr."""
    read(rdr, True, None, True)
    return rdr


class wrappingReader(object):
    """Defines a callable object that reads the next object and returns:
    (sym next-object-read)
    Where sym is Symbol instance passed to __init__."""
    def __init__(self, sym):
        self.sym = sym

    def __call__(self, rdr, quote):
        o = read(rdr, True, None, True)
        return RT.list(self.sym, o)


def dispatchReader(rdr, hash):
    """Read and return the next object defined by the next dispatch character.

    rdr -- read/unread-able object
    hash -- ignored

    Read a character from rdr. Call its associated function in
    dispatchMacros. Return that value. May raise ReaderException."""
    ch = read1(rdr)
    if ch == "":
        raise ReaderException("EOF while reading character", rdr)
    if ch not in dispatchMacros:
        raise ReaderException("No dispatch macro for: ("+ ch + ")", rdr)
    return dispatchMacros[ch](rdr, ch)


def listReader(rdr, leftparen):
    """Read and return a possibly empty list () from rdr.

    rdr -- a read/unread-able object
    leftparen -- ignored"""
    startline = rdr.lineCol()[0]
    lst = readDelimitedList(')', rdr, True)
    lst = apply(RT.list, lst)
    return lst.withMeta(RT.map(LINE_KEY, startline))


def vectorReader(rdr, leftbracket):
    """Read and return a possibly empty vector [] from rdr.

    rdr -- a read/unread-able object
    leftbracket -- ignored"""
    startline = rdr.lineCol()[0]
    lst = readDelimitedList(']', rdr, True)
    lst = apply(RT.vector, lst)
    return lst


def mapReader(rdr, leftbrace):
    """Read and return a possibly empty map {} from rdr.

    rdr -- a read/unread-able object
    leftbrace -- ignored"""
    startline = rdr.lineCol()[0]
    lst = readDelimitedList('}', rdr, True)
    lst = apply(RT.map, lst)
    return lst


def setReader(rdr, leftbrace):
    """Read and return a possibly empty set #{} from rdr.

    rdr -- a read/unread-able object
    leftbrace -- ignored"""
    s = readDelimitedList("}", rdr, True)
    return createWithCheck(s)


def unmatchedClosingDelimiterReader(rdr, un):
    """Raise ReaderException.

    rdr -- read/unread-able object (used for exception message)
    un -- the stray delimiter

    This will be called if un has no matching opening delimiter in rdr."""
    raise ReaderException(
        "Unmatched Delimiter {0} at {1}".format(un, rdr.lineCol()))


def readDelimitedList(delim, rdr, isRecursive):
    """Read and collect objects until an unmatched delim is reached.

    delim -- the terminating delimiter
    rdr -- read/unread-able object
    isRecursive -- ignored

    May raise ReaderException. Return a Python list of those objects."""
    firstline = rdr.lineCol()[0]
    a = []

    while True:
        ch = read1(rdr)
        while ch in whiteSpace:
            ch = read1(rdr)
        if ch == "":
            raise ReaderException(
                "EOF while reading starting at line {0}".format(firstline))

        if ch == delim:
            break

        macrofn = getMacro(ch)
        if macrofn is not None:
            mret = macrofn(rdr, ch)
            if mret is not None and mret is not rdr:
                a.append(mret)
        else:
            rdr.back()
            o = read(rdr, True, None, isRecursive)
            a.append(o)

    return a


# This is the unicode name db Python uses:
# ftp://ftp.unicode.org/Public/5.2.0/ucd/UnicodeData.txt
def readNamedUnicodeChar(rdr):
    """Read \N{foo} syntax, starting at the {.

    rdr -- a read/unread-able object

    May raise ReaderException. Return the unicode character named by foo."""
    buf = []
    ch = read1(rdr)
    if ch != "{":
        raise ReaderException("Expected { in named unicode escape sequence,"
                              " got: ({0})".format(ch or "EOF"), rdr)
    while True:
        ch = read1(rdr)
        if ch == "":
            raise ReaderException("EOF while reading named unicode escape"
                                  " sequence", rdr)
        elif ch in unicodeNameChars:
            buf.append(ch)
            continue
        elif ch == '"':
            raise ReaderException("Missing } while reading named unicode"
                                  " escape sequence", rdr)
        elif ch == '}':
            break
        else:
            raise ReaderException("Illegal character in named unicode"
                                  " escape sequence: ({0})".format(ch), rdr)
    name = "".join(buf).strip()
    if len(name) == 0:
        raise ReaderException("Expected name between {} in named unicode "
                              "escape sequence", rdr)
    try:
        return unicodedata.lookup(name)
    except KeyError:
        raise ReaderException("Unknown unicode character name in escape"
                              " sequence: ({0})".format(name), rdr)


def rawRegexReader(rdr, r):
    r"""Read a regex pattern string ignoring most escape sequences.

    rdr -- a read/unread-able object
    r -- ignored

    The following two are the only valid escape sequences. But only if they
    are not preceded by an even number of backslashes. When \ are in pairs
    they've lost their abilty to escape the next character. Both backslashes
    *still* get put into the string.

      * \uXXXX
        \u03bb => λ
        \\u03bb => \ \ u 0 3 b b
        \\\u03bb => \ \ λ
      * \UXXXXXXXX
        same as above

    Everything else will result in two characters in the string:
    \n => \ n
    \r => \ r
    \t => \ t
    \" => \ "
    \xff => \ x f f
    \377 => \ 3 7 7
    \N{foo} \ N { f o o }

    May raise ReaderException. Return a Unicode string.
    """
    nSlashes = 0
    pat = []
    ch = read1(rdr)
    if ch == "":
        raise ReaderException("EOF expecting regex pattern", rdr)
    if ch != '"':
        raise ReaderException("Expected regex pattern after #r", rdr)
    ch = read1(rdr)
    while ch != '"':
        if ch == "":
            raise ReaderException("EOF while reading regex pattern", rdr)
        if ch == "\\":
            nSlashes += 1
            ch = read1(rdr)
            if ch == "":
                raise ReaderException("EOF while reading regex pattern", rdr)
            # \uXXXX
            elif ch == "u" and nSlashes % 2 != 0:
                ch = read1(rdr)
                if not ch in hexChars:
                    raise ReaderException("Hexidecimal digit expected"
                                          " after \\u in regex pattern,"
                                          " got: ({0})".format(ch or "EOF"),
                                          rdr)
                pat.append(readUnicodeChar(rdr, ch, 16, 4, True))
                nSlashes = 0
            # \uXXXXXXXX
            elif ch == "U" and nSlashes % 2 != 0:
                ch = read1(rdr)
                if not ch in hexChars:
                    raise ReaderException("Hexidecimal digit expected"
                                          " after \\U in regex pattern,"
                                          " got: ({0})".format(ch or "EOF"),
                                          rdr)
                pat.append(readUnicodeChar(rdr, ch, 16, 8, True))
                nSlashes = 0
            else:
                if ch == "\\":
                    nSlashes += 1
                pat.append("\\")
                pat.append(ch)
        else:
            pat.append(ch)
        ch = read1(rdr)
    try:
        return re.compile(u"".join(pat))
    except re.error as e:
        raise ReaderException("invalid regex pattern: {0}".format(e.args[0]),
                              rdr)


def regexReader(rdr, doublequote):
    """Read a possibly multi-line Python re pattern string.

    rdr -- read/unread-able object
    doubleQuote -- ignored
    raw -- if True, the string is to be treated as a Python r"string".

    May raise ReaderException. Return a Unicode string"""
    pat = []
    ch = read1(rdr)
    while ch != '"':
        if ch == "":
            raise ReaderException("EOF while reading regex pattern", rdr)
        if ch == "\\":
            ch = read1(rdr)
            if ch == "":
                raise ReaderException("EOF while reading regex pattern", rdr)
            # \, ', ", a, b, f, n, r, t, v
            elif ch in regexCharLiterals:
                ch = regexCharLiterals[ch]
            # \uXXXX
            elif ch == "u":
                ch = read1(rdr)
                if not ch in hexChars:
                    raise ReaderException("Hexidecimal digit expected after"
                                          " \\u in regex pattern, got:"
                                          " ({0})".format(ch or "EOF"), rdr)
                ch = readUnicodeChar(rdr, ch, 16, 4, True)
            # \uXXXXXXXX
            elif ch == "U":
                ch = read1(rdr)
                if not ch in hexChars:
                    raise ReaderException("Hexidecimal digit expected after"
                                          " \\U in regex pattern, got:"
                                          " ({0})".format(ch or "EOF"), rdr)
                ch = readUnicodeChar(rdr, ch, 16, 8, True)
            # \xXX
            elif ch == "x":
                ch = read1(rdr)
                if not ch in hexChars:
                    raise ReaderException("Hexidecimal digit expected after"
                                          " \\x in regex pattern, got:"
                                          " ({0})".format(ch or "EOF"), rdr)
                ch = readUnicodeChar(rdr, ch, 16, 2, True)
            #\O, \OO, or \OOO
            elif ch.isdigit():
                ch = readUnicodeChar(rdr, ch, 8, 3, False) # <= False
            #\N{named unicode character}
            elif ch == "N":
                ch = readNamedUnicodeChar(rdr)
            # Didnt recognize any escape sequence but ch got
            # reset to the char after \\ so...
            else:
                pat.append("\\")
        pat.append(ch)
        ch = read1(rdr)
    try:
        return re.compile(u"".join(pat))
    except re.error as e:
        raise ReaderException("invalid regex pattern: {0}".format(e.args[0]),
                              rdr)


def metaReader(rdr, caret):
    """Read two objects from rdr. Return second with first as meta data.

    rdr -- read/unread-able object
    caret -- ignored

    May raise ReaderException."""
    line = rdr.lineCol()[0]
    meta = read(rdr, True, None, True)
    if isinstance(meta, (str, Symbol)):
        meta = RT.map(TAG_KEY, meta)
    elif isinstance(meta, Keyword):
        meta = RT.map(meta, T)
    elif not isinstance(meta, IPersistentMap):
        raise ReaderException("Metadata must be Symbol,Keyword,String or Map",
                              rdr)
    o = read(rdr, True, None, True)
    if not hasattr(o, "withMeta"):
        # can't attach rdr to the exception here as it would point
        # to the *end* of the object just read'
        raise ReaderException("Cannot attach meta to a object without"
                              " .withMeta")
    return o.withMeta(meta)

def currentNSName():
    comp = currentCompiler.deref()
    if comp is None:
        raise IllegalStateException("No Compiler found in syntax quote!")
    ns = comp.getNS()
    if ns is None:
        raise IllegalStateException("No ns in reader")
    return ns.__name__

def matchSymbol(s):
    """Return a symbol or keyword.

    Return None if the string s does not define a legal symbol or keyword."""
    m = symbolPat.match(s)
    if m is not None:
        ns = m.group(1)
        name = m.group(2)

        if name.endswith(".") and not name.startswith("."):
            name = name[:-1]
        if ns is not None and (ns.endswith(":/") or name.endswith(":")\
            or s.find("::") != -1):
                return None
        ns = ns if ns is None else ns[:-1]
        
        if s.startswith("::"):
            return Keyword(currentNSName(), s[2:])


        iskeyword = s.startswith(':')
        if iskeyword:
            return Keyword(s[1:])
        else:
            return Symbol(ns, name)
    return None


def argReader(rdr, perc):
    """Read and intern an anonymous function argument (%, %1, %&, etc.).

    rdr -- read/unread-able object
    prec -- ignored

    May raise IllegalStateException, or ReaderException.
    """
    if ARG_ENV.deref() is None:
        return interpretToken(readToken(rdr, '%'))
    ch = read1(rdr)
    rdr.back()
    if ch == "" or ch in whiteSpace or isTerminatingMacro(ch):
        return registerArg(1)
    n = read(rdr, True, None, True)
    if isinstance(n, Symbol) and n == _AMP_:
        return registerArg(-1)
    if not isinstance(n, int):
        raise ReaderException("arg literal must be %, %& or %integer", rdr)
    return registerArg(n)


def varQuoteReader(rdr, singlequote):
    """Return the list (var next-object-read)

    rdr -- read/unread-able object
    singlequote -- ignored"""
    line = rdr.lineCol()[0]
    form = read(rdr, True, None, True)
    return RT.list(_VAR_, form).withMeta(RT.map(LINE_KEY, line))


def registerArg(arg):
    argsyms = ARG_ENV.deref()
    if argsyms is None:
        raise IllegalStateException("arg literal not in #()")
    ret = argsyms[arg]
    if ret is None:
        ret = garg(arg)
        ARG_ENV.set(argsyms.assoc(arg, ret))
    return ret


def fnReader(rdr, lparen):
    """Read an anonymous function #() from reader

    rdr -- a read/unread-able object
    lparen -- ignored

    Return an IPersistentList"""
    if ARG_ENV.deref() is not None:
        raise IllegalStateException("Nested #()s are not allowed")
    with threadBindings(RT.map(ARG_ENV, EMPTY_MAP)):
        rdr.back()
        form = read(rdr, True, None, True)
        drefed = ARG_ENV.deref()
        sargs = sorted(list(filter(lambda x: x != -1, drefed)))
        args = []
        if len(sargs):
            for x in range(1, int(str(sargs[-1])) + 1):
                if x in drefed:
                    args.append(drefed[x])
                else:
                    args.append(garg(x))
            retsym = drefed[-1]
            if retsym is not None:
                args.append(_AMP_)
                args.append(retsym)
        vargs = RT.vector(*args)
    return RT.list(_FN_, vargs, form)


def isUnquote(form):
    """Return True if form is (unquote ...)"""
    return isinstance(form, ISeq) and form.first() == _UNQUOTE_


def isUnquoteSplicing(form):
    """Return True if form is (unquote-splicing ...)"""
    return isinstance(form, ISeq) and form.first() == _UNQUOTE_SPLICING_


class SyntaxQuoteReader(object):
    _HASHMAP_ = Symbol("clojure.core", "hashmap")
    _CONCAT_ = Symbol("clojure.core", "concat")
    _LIST_ = Symbol("clojure.core", "list")
    _SEQ_ = Symbol("clojure.core", "seq")
    _VECTOR_ = Symbol("clojure.core", "vector")

    def __call__(self, r, backquote):
        with threadBindings(RT.map(GENSYM_ENV, EMPTY_MAP)):
            self.rdr = r
            form = read(r, True, None, True)
            return self.syntaxQuote(form)

    def syntaxQuote(self, form):
        # compiler uses this module, so import it lazily
        from clojure.lang.compiler import builtins as compilerbuiltins

        if form in compilerbuiltins:
            ret = RT.list(_QUOTE_, form)
        elif isinstance(form, Symbol):
            sym = form
            if sym.ns is None and sym.name.endswith("#"):
                gmap = GENSYM_ENV.deref()
                if gmap == None:
                    raise ReaderException("Gensym literal not in syntax-quote, before", self.rdr)
                gs = gmap[sym]
                if gs is None:
                    gs = Symbol(None, "{0}__{1}__auto__".format(sym.name[:-1], RT.nextID()))
                    GENSYM_ENV.set(gmap.assoc(sym, gs))
                sym = gs
            elif sym.ns is None and sym.name.endswith("."):
                ret = sym
            elif sym.ns is None and sym.name.startswith("."):
                ret = sym
            elif sym.ns is not None:
                ret = sym

            else:
                comp = currentCompiler.deref()
                if comp is None:
                    raise IllegalStateException("No Compiler found in syntax quote!")
                ns = comp.getNS()
                if ns is None:
                    raise IllegalStateException("No ns in reader")
                
                item = namespace.findItem(ns, sym)
                if item is None:
                    sym = Symbol(ns.__name__, sym.name)
                else:
                    sym = Symbol(item.ns.__name__, sym.name)
            ret = RT.list(_QUOTE_, sym)
        else:
            if isUnquote(form):
                return form.next().first()
            elif isUnquoteSplicing(form):
                raise IllegalStateException("splice not in list")
            elif isinstance(form, IPersistentCollection):
                if isinstance(form, IPersistentMap):
                    keyvals = self.flattenMap(form)
                    ret = RT.list(_APPLY_,
                                  self._HASHMAP_,
                                  RT.list(RT.cons(self._CONCAT_,
                                                  self.sqExpandList(keyvals.seq()))))
                elif isinstance(form, (IPersistentVector, IPersistentSet)):
                    ret = RT.list(_APPLY_,
                                  self._VECTOR_,
                                  RT.list(self._SEQ_,
                                          RT.cons(self._CONCAT_,
                                                  self.sqExpandList(form.seq()))))
                elif isinstance(form, (ISeq, IPersistentList)):
                    seq = form.seq()
                    if seq is None:
                        ret = RT.cons(self._LIST_, None)
                    else:
                        ret = RT.list(self._SEQ_,
                                      RT.cons(self._CONCAT_, self.sqExpandList(seq)))
                else:
                    raise IllegalStateException("Unknown collection type")
            elif isinstance(form, (int, float, str, Keyword)):
                ret = form
            else:
                ret = RT.list(_QUOTE_, form)
        if getattr(form, "meta", lambda: None)() is not None:
            newMeta = form.meta().without(LINE_KEY)
            if len(newMeta) > 0:
                return RT.list(_WITH_META_, ret, self.syntaxQuote(form.meta()))#FIXME: _WITH_META_ undefined
        return ret

    def sqExpandList(self, seq):
        ret = EMPTY_VECTOR
        while seq is not None:
            item = seq.first()
            if isUnquote(item):
                ret = ret.cons(RT.list(self._LIST_, item.next().first()))
            elif isUnquoteSplicing(item):
                ret = ret.cons(item.next().first())
            else:
                ret = ret.cons(RT.list(self._LIST_, self.syntaxQuote(item)))
            seq = seq.next()
        return ret.seq()

    def flattenMap(self, m):
        keyvals = EMPTY_VECTOR
        s = m.seq()
        while s is not None:
            e = s.first()
            keyvals = keyvals.cons(e.getKey())
            keyvals = keyvals.cons(e.getValue())
            s = s.next()
        return keyvals


def garg(n):
    return Symbol("rest" if n == -1 else "p{0}__{1}#".format(n, RT.nextID()))


def derefNotImplemented(rdr, _):
    """Unconditionally raise ReaderException.

    The deref syntax @foo is not currently implemented. @foo will pass through
    silently as a symbol unless it's caught here, as it should be."""
    raise ReaderException("Deref syntax @foo not currently implemented.",
                          rdr)


def evalReaderNotImplemented(rdr, _):
    """Unconditionally raise ReaderException.

    The eval syntax #= not currently implemented and should be caught by the
    #reader. This message is more informative than the `no dispatch macro'
    message."""
    raise ReaderException("Eval syntax #= not currently implemented.",
                          rdr)


macros = {'\"': stringReader,
          "\'": wrappingReader(_QUOTE_),
          "(": listReader,
          ")": unmatchedClosingDelimiterReader,
          "[": vectorReader,
          "]": unmatchedClosingDelimiterReader,
          "{": mapReader,
          "}": unmatchedClosingDelimiterReader,
          ";": commentReader,
          "#": dispatchReader,
          "^": metaReader,
          "%": argReader,
          "`": SyntaxQuoteReader(),
          "~": unquoteReader,
          "\\": characterReader,
          "@": wrappingReader(_DEREF_)
          }

dispatchMacros = {"\"": regexReader,
                  "{": setReader,
                  "!": commentReader,
                  "_": discardReader,
                  "(": fnReader,
                  "'": varQuoteReader,
                  "^": metaReader,
                  # Use Python raw string syntax as #r"foo"
                  "r": rawRegexReader,
                  "=": evalReaderNotImplemented, # temporary?
                  }
