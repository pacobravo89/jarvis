import unittest
from jarvis.audio import normalize,wake
from jarvis.tools import allowed_path
class Basic(unittest.TestCase):
    def test_wake(self):self.assertEqual(wake('Jarvis, hola'),(True,'hola'))
    def test_normalize(self):self.assertEqual(normalize('Adiós, JARVIS!'),'adios jarvis')
    def test_block_path(self):
        with self.assertRaises(PermissionError):allowed_path('C:/Windows/System32/config/SAM')
if __name__=='__main__':unittest.main()
