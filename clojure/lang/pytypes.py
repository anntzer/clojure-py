"""pytypes.py

Saturday, March 24 2012
"""

import re                       # for compiled regex type
import types                    # for generators, etc.

pyObjectType = object
pyRegexType = type(re.compile(""))
pyFuncType = types.FunctionType
pyListType = list
pySetType = set
pyTupleType = tuple
pyDictType = dict
pyStrType = str
pyUnicodeType = unicode
pyNoneType = types.NoneType
pyBoolType = bool
pyIntType = int
pyLongType = long
pyFloatType = float
pyFileType = file
pyTypeType = type
pyTypeCode = types.CodeType
pyTypeGenerator = types.GeneratorType
pyClassType = types.ClassType
pyReversedType = reversed

# add more if needed
