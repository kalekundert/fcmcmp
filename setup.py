#!/usr/bin/env python3

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

with open('fcmcmp/__meta__.py') as file:
    exec(file.read())
with open('README.rst') as file:
    readme = file.read()

setup(
    name='fcmcmp',
    version=__version__,
    author=__author__,
    author_email=__email__,
    description="A lightweight, flexible, and modern framework for annotating flow cytometry data.",
    long_description=readme,
    url='https://github.com/kalekundert/fcmcmp',
    packages=[
        'fcmcmp',
    ],
    include_package_data=True,
    install_requires=[
        'fcsparser',
        'pyyaml',
        'pathlib',
        'pandas',
        'scipy',
    ],
    license='MIT',
    zip_safe=False,
    keywords=[
        'fcmcmp',
    ],
)
