import re

from setuptools import setup


MODULE_NAME = 'simplebot_help'
CLASS_NAME = 'Helper'
with open(MODULE_NAME+'.py', 'rt', encoding='utf8') as fh:
    source = fh.read()
PLUGIN_NAME = re.search(r'name = \'(.*?)\'', source, re.M).group(1)
DESCRIPTION = re.search(r'description = \'(.*?)\'', source, re.M).group(1)
VERSION = re.search(r'version = \'(.*?)\'', source, re.M).group(1)
AUTHOR = re.search(r'author = \'(.*?)\'', source, re.M).group(1)


setup(
    name=MODULE_NAME,
    version=VERSION,
    license='GPL3+',
    author=AUTHOR,
    author_email='adbenitez@nauta.cu',
    description=DESCRIPTION,
    long_description=DESCRIPTION,
    long_description_content_type='text/x-rst',
    url='https://github.com/adbenitez/simplebot_plugins',
    classifiers=(
        'Development Status :: 3 - Alpha',
        'Environment :: Plugins',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Topic :: Utilities'
    ),
    keywords='deltachat simplebot plugin',
    #project_urls={},
    py_modules=[MODULE_NAME],
    install_requires=['simplebot'],
    python_requires='>=3.5',
    entry_points={
        'simplebot.plugins': '{} = {}:{}'.format(PLUGIN_NAME, MODULE_NAME, CLASS_NAME)
    },
)
