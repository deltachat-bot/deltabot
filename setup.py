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
    description='Pluginable Delta Chat bot',
    long_description=long_desc,
    long_description_content_type='text/x-rst',
    author='The SimpleBot Contributors',
    author_email='adbenitez@nauta.cu',
    url='https://github.com/SimpleBot-Inc/simplebot',
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
    install_requires=['click>=6.0', 'deltachat', 'html2text'],
    include_package_data=True,
    zip_safe=False,
)
