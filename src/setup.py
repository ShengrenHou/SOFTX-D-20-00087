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


from setuptools import setup, find_packages


setup(
    name='pycity_scheduling',
    description='A Python framework for the development and assessment of optimisation-based power scheduling'
                'algorithms for multi-energy systems in city districts',
    version='0.9',
    author='Sebastian Schwarz, Sebastian Alexander Uerlich, Antonello Monti'
           'Institute for Automation of Complex Power Systems'
           'E.ON Energy Research Center, RWTH Aachen University',
    author_email='post_acs@eonerc.rwth-aachen.de',
    url='https://www.acs.eonerc.rwth-aachen.de/cms/~dlkd/E-ON-ERC-ACS/',
    license='MIT',
    license_file='LICENSE.txt',
    packages=find_packages(),
    package_data={'pycity_scheduling': ['data/*.txt']},
    install_requires=[
        'numpy',
        'pandas',
        'matplotlib',
        'pyomo',
        'Shapely',
        'pycity_base>=0.3.1'
    ],
    extras_require={
        'test': ['pytest']
    },
    platforms='any',
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Scientists/Engineers/Developers",
        "License :: OSI Approved :: MIT License",
        "Topic :: Science/Engineering",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.6",
    ],
    zip_safe=False
)
