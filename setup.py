import os
import setuptools

def main():
    with open(os.path.join("src","deltabot", "__init__.py")) as f:
        for line in f:
            if "__version__" in line.strip():
                version = line.split("=", 1)[1].strip().strip('"')
                break

    with open("README.rst") as f:
        long_desc = f.read()

    setuptools.setup(
        name='deltabot',
        description='Delta.Chat bot to reply to incoming messages in groups or 1:1 chats',
        long_description = long_desc,
        version=version,
        url='https://github.com/hpk42/deltabot',
        license='GPL',
        platforms=['unix', 'linux', 'osx', 'cygwin', 'win32'],
        author='holger krekel',
        author_email='holger@merlinux.eu',
        package_dir={'': 'src'},
        packages = setuptools.find_packages('src'),
        classifiers=['Development Status :: 3 - Alpha',
                     'Intended Audience :: Developers',
                     'License :: OSI Approved :: MIT License',
                     'Operating System :: POSIX',
                     'Operating System :: MacOS :: MacOS X',
                     'Topic :: Utilities',
                     'Intended Audience :: Developers',
                     'Programming Language :: Python'],
        entry_points='''
            [console_scripts]
            deltabot=deltabot.cmdline:bot_main
        ''',
        install_requires = ["click>=6.0", "deltachat>=0.8.0"],
        zip_safe=False,
    )

if __name__ == '__main__':
    main()

