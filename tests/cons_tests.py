"""cons_tests.py

Friday, March 30 2012
"""

import re
import unittest
from cStringIO import StringIO

from clojure.lang.cons import Cons
import clojure.lang.persistentlist as pl
from clojure.lang.persistentlist import EmptyList
from clojure.lang.cljexceptions import ArityException
from clojure.protocols import ISeq

uobj = object()
pseudoMetaData = object()

class TestCons(unittest.TestCase):
    def setUp(self):
        # if this raises no exceptions, the others will validate creation
        self.head = "head"
        self.t1 = pl.creator(uobj)
        self.t2 = pl.creator(0, uobj)
        self.t3 = pl.creator(0, 1, uobj)
        self.c1 = Cons(self.head, None)
        self.c2 = Cons(self.head, self.t1)
        # e.g. ("head" 0 uobj)
        self.c3 = Cons(self.head, self.t2)
        self.c4 = Cons(self.head, self.t3)
        # just checking printed structure
        self.printS = Cons(pl.creator(1, 2),
                           pl.creator(pl.creator(3, 4)))
    def test__init___FAIL(self):
        self.assertRaises(ArityException, Cons)
        self.assertRaises(ArityException, Cons, 1, 2, 3, 4)
    # next()
    def testNext_PASS(self):
        c = self.c2.next()
        self.assertTrue(isinstance(c, ISeq))
        self.assertEqual(c.next(), None)
    # first()
    def testFirst_PASS(self):
        self.assertEqual(self.c1.first(), "head")
    # __len__
    def test__len___PASS(self):
        self.assertEqual(self.c1.__len__(), 1)
        self.assertEqual(self.c2.__len__(), 2)
        self.assertEqual(self.c3.__len__(), 3)
        self.assertEqual(self.c4.__len__(), 4)
    # withMeta()
    def testWithMeta_PASS(self):
        c2 = self.c2.withMeta(pseudoMetaData)
        self.assertEqual(c2.meta(), pseudoMetaData)
    # (print s)
    def testWriteAsString_PASS(self):
        csio = StringIO()
        self.printS.writeAsString(csio)
        self.assertEqual(csio.getvalue(), "((1 2) (3 4))")
    # (pr s)
    def testWriteAsReplString_PASS(self):
        csio = StringIO()
        self.printS.writeAsReplString(csio)
        self.assertEqual(csio.getvalue(), "((1 2) (3 4))")
    # str(s)
    def test__str___PASS(self):
        self.assertEqual(self.printS.__str__(), "((1, 2), (3, 4))")
    # make sure the correct namespace is printed
    # repr(s)
    def test__repr___PASS(self):
        regex = r"<clojure\.lang\.cons\.Cons" \
                r" object at 0x[a-fA-F0-9]+ \(\(1 2\) \(3 4\)\)>$"
        self.assertTrue(re.match(regex, self.printS.__repr__()))
