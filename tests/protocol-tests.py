from clojure.lang.protocol import ProtocolFn
import unittest

class TestProtocolFunctions(unittest.TestCase):
    def testProtocol(self):
        z = ProtocolFn(None, "foo")
        z.extend(int, lambda x: "int")
        z.extend(ProtocolFn, lambda f: "fn")
        z.extend(float, lambda f: "float")
        
        self.assertEqual(z(1), "int")
        self.assertEqual(z(1.0), "float")
        self.assertEqual(z(z), "fn")
        
