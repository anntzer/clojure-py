"""mapentry_tests.py

Wednesday, March 28 2012
"""

import unittest

import clojure.lang.mapentry as me
from clojure.lang.apersistentvector import SubVec
from clojure.lang.persistentvector import PersistentVector
from clojure.lang.cljexceptions import IndexOutOfBoundsException
from clojure.protocols import ISeq


class TestMapEntry(unittest.TestCase):
    def setUp(self):
        self.mapEntry = me.MapEntry("key", "value")
    def testGetKey_PASS(self):
        self.assertEqual(self.mapEntry.getKey(), "key")
    def testGetValue_PASS(self):
        self.assertEqual(self.mapEntry.getValue(), "value")
    def test__getitem___PASS(self):
        self.assertEqual(self.mapEntry[0], "key")
        self.assertEqual(self.mapEntry[1], "value")
    def test__getitem___FAIL(self):
        self.assertRaises(IndexOutOfBoundsException,
                          self.mapEntry.__getitem__, -1)
        self.assertRaises(IndexOutOfBoundsException,
                          self.mapEntry.__getitem__, 2)
    def testAsVector_PASS(self):
        v = self.mapEntry.asVector()
        self.assertTrue(isinstance(v, PersistentVector))
        self.assertEqual(len(v), 2)
        self.assertEqual(v.nth(0), "key")
        self.assertEqual(v.nth(1), "value")
    def testAssocN_PASS(self):
        v1 = self.mapEntry.assocN(0, "yek")
        self.assertTrue(isinstance(v1, PersistentVector))
        self.assertEqual(len(v1), 2)
        self.assertEqual(v1.nth(0), "yek")
        self.assertEqual(v1.nth(1), "value")
        v2 = self.mapEntry.assocN(1, "eulav")
        self.assertTrue(isinstance(v2, PersistentVector))
        self.assertEqual(len(v2), 2)
        self.assertEqual(v2.nth(0), "key")
        self.assertEqual(v2.nth(1), "eulav")
    def testAssocN_FAIL(self):
        self.assertRaises(IndexOutOfBoundsException,
                          self.mapEntry.assocN, 3, "yek")
    def test__len___Pass(self):
        self.assertEqual(len(self.mapEntry), 2)
    def test__contains___Pass(self):
        self.assertTrue(0 in self.mapEntry)
        self.assertTrue(1 in self.mapEntry)
    def testSeq_PASS(self):
        s = self.mapEntry.seq()
        self.assertTrue(isinstance(s, ISeq))
        self.assertTrue(len(s), 2)
        self.assertTrue(s.first(), "key")
        self.assertTrue(s.next().first(), "value")
    def testCons_PASS(self):
        v = self.mapEntry.cons("foo")
        self.assertTrue(isinstance(v, PersistentVector))
        self.assertEqual(len(v), 3)
        self.assertEqual(v.nth(0), "key")
        self.assertEqual(v.nth(1), "value")
        self.assertEqual(v.nth(2), "foo")
    def testEmpty_PASS(self):
        self.assertEqual(self.mapEntry.empty(), None)
    def testPop_PASS(self):
        v = self.mapEntry.pop()
        self.assertTrue(isinstance(v, PersistentVector))
        self.assertEqual(len(v), 1)
        self.assertEqual(v.nth(0), "key")


