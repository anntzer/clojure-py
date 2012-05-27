"""persistentlist_tests.py

Thursday, March 29 2012
"""

import re
import unittest
import operator
from cStringIO import StringIO

import clojure.lang.persistentlist as pl
from clojure.lang.persistentlist import PersistentList, EmptyList
from clojure.lang.cljexceptions import (ArityException,
                                        IndexOutOfBoundsException)
from clojure.protocols import ISeq

uobj = object()
pseudoMetaData = object()

def seqHash(v):
    """Duplicates ASeq.hasheq()"""
    h = 1
    for e in v:
        h = 31 * h + hash(e)
    return h

class TestPersistentList(unittest.TestCase):
    def setUp(self):
        # if this raises no exceptions, the others will validate creation
        self.l0 = pl.creator()
        self.l1 = pl.creator(uobj)
        self.l2 = pl.creator(0, uobj)
        self.l3 = pl.creator(0, 1, uobj)
        self.lR = pl.creator(1, 2, 3, 4, 5) # for reduce test
        # just checking printed structure
        self.printS = pl.creator(pl.creator(1, 2),
                                 pl.creator(3, 4))
    # next()
    def testNext_PASS(self):
        l = self.l2.next()
        self.assertTrue(isinstance(l, ISeq))
        self.assertEqual(l.next(), None)
    # first()
    def testFirst_PASS(self):
        self.assertEqual(self.l0.first(), None)
        self.assertEqual(self.l1.first(), uobj)
    # peek()
    def testPeek_PASS(self):
        self.assertEqual(self.l0.peek(), None)
        self.assertEqual(self.l1.peek(), uobj)
    # pop()
    def testPop_PASS(self):
        l = self.l2.pop()
        self.assertEqual(len(l), 1)
        self.assertEqual(l.first(), uobj)
        self.assertTrue(isinstance(l.pop(), EmptyList))
        
    # No fail test for pop(). There is no empty PersistentList. It's an
    # EmptyList instance instead.
        
    # __len__
    def test__len___PASS(self):
        self.assertEqual(self.l0.__len__(), 0)
        self.assertEqual(self.l1.__len__(), 1)
        self.assertEqual(self.l2.__len__(), 2)
        self.assertEqual(self.l3.__len__(), 3)
    # cons()
    def testCons_PASS(self):
        l1 = self.l0.cons("consed")
        self.assertEqual(len(l1), 1)
        self.assertEqual(l1.first(), "consed")
        l2 = self.l1.cons("consed")
        self.assertEqual(len(l2), 2)
        self.assertEqual(l2.first(), "consed")
    # empty()
    def testEmpty_PASS(self):
        l0 = self.l3.empty()
        self.assertTrue(isinstance(l0, EmptyList))
        self.assertEqual(len(l0), 0)
    # reduce()
    def testReduce_PASS(self):
        # list with one item
        x = pl.creator(42).reduce(operator.add)
        self.assertEqual(x, 42)
        x = pl.creator(42).reduce(operator.add, 42)
        self.assertEqual(x, 84)
        x = pl.creator(42).reduce(operator.add, -42)
        self.assertEqual(x, 0)
        # list with more than one item
        x = self.lR.reduce(operator.add)
        self.assertEqual(x, 15)
        x = self.lR.reduce(operator.add, 5)
        self.assertEqual(x, 20)
        x = self.lR.reduce(operator.add, -15)
        self.assertEqual(x, 0)
        # Can't test an empty PersistentList because EmptyList has no reduce
        # method
    def testReduce_FAIL(self):
        # not enough arguments
        self.assertRaises(ArityException, self.l1.reduce)
        # too many
        self.assertRaises(ArityException, self.l1.reduce, 1, 2, 3)
    # withMeta()
    def testWithMeta_PASS(self):
        # return self
        l1 = self.l1.withMeta(pseudoMetaData)
        l2 = l1.withMeta(pseudoMetaData)
        self.assertTrue(l1 is l2)
        self.assertTrue(l1.meta() is l2.meta())
        # return new PersistentList
        l3 = self.l3.withMeta(uobj)
        self.assertTrue(l3 is not self.l3)
        self.assertTrue(uobj, l3.meta())

    # ASeq methods
        
    # TODO: check equality again
    # __eq__
    def test__eq___PASS(self):
        # only tests simple PersistentList's
        self.assertTrue(self.l1.__eq__(self.l1))
        self.assertTrue(self.l1.__eq__(pl.creator(uobj)))
    # __ne__
    def test__ne___PASS(self):
        # only tests simple PersistentList's
        self.assertFalse(self.l1.__ne__(self.l1))
        self.assertFalse(self.l1.__ne__(pl.creator(uobj)))
    # __getitem__
    def test__getitem___PASS(self):
        self.assertEqual(self.l3[0], 0)
        self.assertEqual(self.l3[1], 1)
        self.assertEqual(self.l3[2], uobj)
    #
    # XXX: These are broken
    # 
    # def test__getitem___FAIL(self):
    #     self.assertRaises(IndexOutOfBoundsException, self.l1.__getitem__, 1)
    #     self.assertRaises(IndexOutOfBoundsException, self.l1.__getitem__, -1)
    # seq()
    def testSeq_PASS(self):
        self.assertTrue(self.l1.seq() is self.l1)
    # more()
    def testMore_PASS(self):
        l1 = self.l2.more()
        self.assertEqual(l1.first(), uobj)
        l0 = self.l1.more()
        self.assertTrue(isinstance(l0, EmptyList))
    # __iter__()
    def test__iter___PASS(self):
        x, y, z = self.l3
        self.assertEqual(x, 0)
        self.assertEqual(y, 1)
        self.assertEqual(z, uobj)
    # TODO: check equality again
    def testHashEq_PASS(self):
        self.assertEqual(self.l1.hasheq(), seqHash(self.l1))
        self.assertEqual(self.l2.hasheq(), seqHash(self.l2))
        self.assertEqual(self.l3.hasheq(), seqHash(self.l3))
        self.assertEqual(self.lR.hasheq(), seqHash(self.lR))
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
    # repr(s)
    def test__repr___PASS(self):
        regex = r"<clojure\.lang\.persistentlist\.PersistentList" \
                r" object at 0x[a-fA-F0-9]+ \(\(1 2\) \(3 4\)\)>$"
        self.assertTrue(re.match(regex, self.printS.__repr__()))
