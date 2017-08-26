from codecs import open
import re
from setuptools import setup


def get_long_description():
    with open('README.md', encoding='utf-8') as f:
        return f.read()


def get_version():
    pattern = r'^__version__ = \'([^\']*)\''
    with open('wake/__init__.py', encoding='utf-8') as f:
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
    author_email='github@lojoja.com',
    license='MIT',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7'
    ],
    packages=['wake'],
    install_requires=[
        'click>=5.0',
        'click_log>=0.1.8',
        'ipaddress>=1.0.18',
        'marshmallow>=2.13.6',
        'texttable>=0.9.1'
    ],
    entry_points={
        'console_scripts': [
            'wake=wake.cli:cli'
        ]
    }
)
