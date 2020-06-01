#!/usr/bin/env python
# coding: utf-8

import os
from setuptools import setup

requirements = [
    'tornado >= 4.5.2, < 6.0.0'
]

f = open(os.path.join(os.path.dirname(__file__), 'README.rst'))
long_description = f.read()
f.close()

__version__ = ""
exec(open('gor/version.py').read())

setup(
    name='gor',
    version=__version__,
    description='Python library for GoReplay Middleware',
    long_description=long_description,
    url='http://github.com/amyangfei/GorMW',
    author='Yang Fei',
    author_email='amyangfei@gmail.com',
    maintainer='Yang Fei',
    maintainer_email='amyangfei@gmail.com',
    keywords=['GoReplay Middleware'],
    license='MIT',
    packages=["gor"],
    include_package_data=True,
    install_requires=requirements,
    test_suite='nose.collector',
    tests_require=[
        'nose',
    ]
)
