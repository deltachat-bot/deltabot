# -*- coding: utf-8 -*-
import re
import os

from setuptools import setup


MODULE_NAME = 'simplebot'
with open(os.path.join(MODULE_NAME, '__init__.py')) as fd:
    version = re.search(r'__version__ = \'(.*?)\'', fd.read(), re.M).group(1)

with open('README.rst') as f:
    long_desc = f.read()


setup(
    name=MODULE_NAME,
    version=version,
    description='Delta Chat bot that does nothing, whew!',
    long_description=long_desc,
    long_description_content_type='text/x-rst',
    author='Asiel Díaz Benítez',
    author_email='adbenitez@nauta.cu',
    url='https://github.com/adbenitez/simplebot',
    packages=[MODULE_NAME],
    classifiers=['Development Status :: 3 - Alpha',
                 'Intended Audience :: Developers',
                 'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
                 'Operating System :: POSIX',
                 'Operating System :: MacOS :: MacOS X',
                 'Topic :: Utilities',
                 'Programming Language :: Python :: 3'],
    entry_points='''
        [console_scripts]
        simplebot=simplebot.cmdline:bot_main
    ''',
    python_requires='>=3.5',
    install_requires=['click>=6.0', 'deltachat>=0.600.0'],
    include_package_data=True,
    zip_safe=False,
)
