"""persistenthashset_tests.py

Friday, March 30 2012
"""

import re
import unittest
from cStringIO import StringIO

from clojure.lang.persistenthashset import PersistentHashSet
from clojure.lang.persistenthashset import create, createWithCheck
from clojure.lang.persistenthashset import EMPTY_MAP, EMPTY as EMPTY_SET
from clojure.lang.cljexceptions import (ArityException,
                                        IllegalArgumentException)
from clojure.protocols import ISeq

uobj = object()
pseudoMetaData = object()

def sethash(s):
    """Duplicate APersistentSet.__hash__().  This is as useless as the other
    hash *tests*. It's more of a bookmark than anything."""
    hsh = 0
    s = s.seq()
    while s is not None:
        e = s.first()
        if isinstance(e, PersistentHashSet):
            hsh += sethash(e)
        else:
            hsh += hash(e)
        s = s.next()
    return hsh

class TestPersistentHashSet(unittest.TestCase):
    def setUp(self):
        self.s0 = EMPTY_SET
        self.s2 = create(1, uobj)
        self.printS = create(1, self.s0)
    # cons()
    def testCons_PASS(self):
        s1 = self.s0.cons(uobj)
        self.assertEqual(len(s1), 1)
        # silent omission of the duplicate, same as Clojure
        s1_1 = s1.cons(uobj)
        self.assertEqual(len(s1_1), 1)
    # meta()
    def testMeta_PASS(self):
        self.assertEqual(self.s0.meta(), None)
        s0meta = PersistentHashSet(pseudoMetaData, EMPTY_MAP)
        self.assertEqual(s0meta.meta(), pseudoMetaData)
    # withMeta()
    def testWithMeta_PASS(self):
        s0meta = self.s0.withMeta(pseudoMetaData)
        self.assertTrue(s0meta is not self.s0)
        self.assertTrue(s0meta.meta() is not self.s0.meta())
        self.assertEqual(s0meta.meta(), pseudoMetaData)
    # empty()
    def testEmpty_PASS(self):
        s1 = self.s0.cons(uobj)
        s1empty = s1.empty()
        self.assertTrue(s1empty is not s1)
        self.assertEqual(len(s1empty), 0)
    # disjoin()
    def testDisjoin_PASS(self):
        s1 = self.s0.cons(uobj)
        # key not a member, return self
        s0 = s1.disjoin("foo")
        self.assertTrue(s0 is s1)
        self.assertEqual(len(s0), 1)
        # key found
        s0 = s1.disjoin(uobj)
        self.assertTrue(s0 is not s1)
        self.assertEqual(len(s0), 0)
    # create()
    def testCreate_PASS(self):
        s3 = create("foo", 3.0, 9)
        self.assertEqual(len(s3), 3)
        # TODO: how shall we handle this difference from Clojure?
        # s3 = create("foo", 3.0, 3)
        # self.assertEqual(len(s3), 3)   # => 2, not 3
    # createWithCheck()
    def testCreateWithCheck_PASS(self):
        s3 = createWithCheck(["foo", 3.0, 9])
        self.assertEqual(len(s3), 3)
    def testCreateWithCheck_FAIL(self):
        self.assertRaises(IllegalArgumentException, createWithCheck, [9, 9])

    # APersistentSet methods

    # __getitem__()
    def test__getitem___PASS(self):
        self.assertEqual(self.s2.__getitem__(uobj), uobj)
        self.assertEqual(self.s2.__getitem__("foo"), None)
    # __contains__()
    def test__getitem___PASS(self):
        self.assertTrue(self.s2.__contains__(uobj))
        self.assertFalse(self.s2.__contains__("foo"))
        self.assertFalse(self.s0.__contains__("foo"))
    # __len__()
    def test__len___PASS(self):
        self.assertEqual(self.s0.__len__(), 0)
        self.assertEqual(self.s2.__len__(), 2)
    # seq()
    def testSeq_PASS(self):
        self.assertEqual(self.s0.seq(), None)
        seq = self.s2.seq()
        self.assertTrue(isinstance(seq, ISeq))
        first = seq.first()
        second = seq.next().first()
        self.assertTrue(first == 1 or first == uobj)
        self.assertTrue(second == 1 or second == uobj)
        self.assertTrue(second != first)
    # __call__()
    def test__call___PASS(self):
        self.assertEqual(self.s2.__call__(uobj), uobj)
        self.assertFalse(self.s0.__call__(None))
    def test__call___FAIL(self):
        # not enough args
        self.assertRaises(ArityException, self.s0.__call__)
        # too many
        self.assertRaises(ArityException, self.s0.__call__, 1, 2)
    # TODO: check equality again
    def test__eq___PASS(self):
        # simple tests here
        self.assertTrue(self.s2.__eq__(self.s2))
        self.assertFalse(self.s2.__eq__("foo"))
        self.assertTrue(self.s2.__eq__(create(1, uobj)))
        self.assertTrue(self.s2.__eq__(create(uobj, 1)))
    # TODO: check hash again
    def test__hash___PASS(self):
        s = create(1, 2, "foo", 3.3, create(1, 2, "bar"))
        self.assertEqual(s.__hash__(), sethash(s))
    # (print s)
    def testWriteAsString_PASS(self):
        csio = StringIO()
        self.printS.writeAsString(csio)
        outstr = csio.getvalue()
        self.assertTrue(outstr == "#{1 #{}}" or outstr == "#{#{} 1}")
    # (pr s)
    def testWriteAsReplString_PASS(self):
        csio = StringIO()
        self.printS.writeAsReplString(csio)
        outstr = csio.getvalue()
        self.assertTrue(outstr == "#{1 #{}}" or outstr == "#{#{} 1}")
    # str(s)
    def test__str___PASS(self):
        outstr = self.printS.__str__()
        self.assertTrue(outstr == "set([1, set()])"
                        or outstr == "set([set(), 1])")
    # repr(s)
    def test__repr___PASS(self):
        regex = r"<clojure\.lang\.persistenthashset\.PersistentHashSet" \
                r" object at 0x[a-fA-F0-9]+" \
                r" (#\{#\{\} 1\}|#\{1 #\{\}\})>$"
        self.assertTrue(re.match(regex, self.printS.__repr__()))
