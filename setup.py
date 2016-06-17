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
        'docopt',
        'fcsparser',
        'natsort',
        'pandas',
        'pathlib',
        'pyyaml',
        'scipy',
    ],
    license='MIT',
    zip_safe=False,
    keywords=[
        'fcmcmp',
    ],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
    ],
)
