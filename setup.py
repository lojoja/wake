import pathlib
import re
from setuptools import setup, find_packages


def get_long_description():
    with pathlib.Path('README.md').open() as f:
        return f.read()


def get_version():
    pattern = r'^__version__ = \'([^\']*)\''
    with pathlib.Path('wake/__init__.py').open() as f:
        text = f.read()
    match = re.search(pattern, text, re.M)

    if match:
        return match.group(1)
    raise RuntimeError('Unable to determine version')


setup(
    name='wake',
    version=get_version(),
    description='A simple wakeonlan implementation.',
    long_description=get_long_description(),
    url='https://github.com/lojoja/wake',
    author='lojoja',
    author_email='dev@lojoja.com',
    license='MIT',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
    ],
    packages=find_packages(),
    data_files=[
        ('/usr/local/etc', ['wake.example.json'])
    ],
    install_requires=[
        'click==8.0.3',
        'marshmallow==3.14.1',
        'texttable==1.6.4'
    ],
    entry_points={
        'console_scripts': [
            'wake=wake.core:cli'
        ]
    },
)
