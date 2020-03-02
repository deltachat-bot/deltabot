# -*- coding: utf-8 -*-
import re
import os

import setuptools


if __name__ == "__main__":
    MODULE_NAME = 'deltabot'

    with open('README.rst') as f:
        long_desc = f.read()


    setuptools.setup(
        name=MODULE_NAME,
        description='Delta Chat bot running and implementation plugin system',
        setup_requires=['setuptools_scm'],
        use_scm_version = True,
        long_description=long_desc,
        long_description_content_type='text/x-rst',
        author='The Deltabot Contributors',
        author_email='adbenitez@nauta.cu, holger@merlinux.eu',
        url='https://github.com/deltachat-bot/deltabot',
        package_dir={'': 'src'},
        packages = setuptools.find_packages('src'),
        classifiers=['Development Status :: 4 - Beta',
                     'Intended Audience :: Developers',
                     'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
                     'Operating System :: POSIX',
                     'Operating System :: MacOS :: MacOS X',
                     'Topic :: Utilities',
                     'Programming Language :: Python :: 3'],
        entry_points='''
            [console_scripts]
            deltabot=deltabot.cmdline:bot_main
        ''',
        python_requires='>=3.5',
        install_requires=['click>=6.0', 'deltachat', 'html2text'],
        include_package_data=True,
        zip_safe=False,
    )
