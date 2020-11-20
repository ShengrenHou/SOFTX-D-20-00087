"""
The pycity_scheduling framework


Copyright (C) 2020
Institute for Automation of Complex Power Systems (ACS);
E.ON Energy Research Center;
RWTH Aachen University

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


import numpy as np
import unittest
import os
from importlib.machinery import SourceFileLoader


class TestExamples(unittest.TestCase):
    def setUp(self):
        this_dir = os.path.dirname(__file__)
        self.example_dir = os.path.join(this_dir, "../../examples")
        self.files = os.listdir(self.example_dir)
        if len(self.files) == 0:
            self.skipTest("No example files found.")
        return

    def test_all_examples(self):
        for file in self.files:
            filepath = os.path.join(self.example_dir, file)
            example_name, file_ext = os.path.splitext(os.path.split(filepath)[-1])
            if file_ext.lower() == '.py':
                example_module = SourceFileLoader('main', filepath).load_module()
                example_module.main(do_plot=False)
        return
