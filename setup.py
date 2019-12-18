from io import open
from os import path

from setuptools import setup, Extension

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

SOURCES = ['src/zx7.c', 'src/optimize.c', 'src/compress.c']

setup(

    name='pyzx7',  # Required

    version='0.0.3',  # Required

    description='ZX7 library Python integration',
    long_description=long_description,  # Optional
    long_description_content_type='text/markdown',  # Optional (see note above)
    url='https://github.com/jsmolina/pyzx7',  # Optional
    packages=['pyzx7'],
    ext_modules=[
        Extension(name="pyzx7/zx7",
                  sources=SOURCES,
                  include_dirs=['src'])
    ],
    author='jsmolina',
)
