# -*- coding: utf-8 -*-
import os
import setuptools

def main():
    with open(os.path.join("src","simplebot", "__init__.py")) as f:
        for line in f:
            if "__version__" in line.strip():
                version = line.split("=", 1)[1].strip().strip('"')
                break

    with open("README.rst") as f:
        long_desc = f.read()

    setuptools.setup(
        name='simplebot',
        description='Delta Chat bot that does nothing, whew!',
        long_description = long_desc,
        version=version,
        url='https://github.com/adbenitez/simplebot',
        license='GPL',
        platforms=['unix', 'linux', 'osx', 'cygwin', 'win32'],
        author='Asiel Díaz Benítez',
        author_email='adbenitez@nauta.cu',
        package_dir={'': 'src'},
        packages = setuptools.find_packages('src'),
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
        install_requires = ["click>=6.0", "deltachat>=0.8.0"],
        zip_safe=False,
    )

if __name__ == '__main__':
    main()

