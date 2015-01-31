#!/usr/bin/env python
# vim: set ts=4 sw=4 tw=0 filetype=python et:
from setuptools import setup, find_packages

setup(
    name = 'ssh_client_cmdline',
    version = '0.1',
    author = 'Jamie Beverly',
    author_email = 'jamie.beverly@yahoo.com',
    packages = ['ssh_client_cmdline'],
    scripts = ['bin/fqdn_ssh_wrapper'], 
    classifiers = [
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
    ],
    test_suite='nose.collector',
    tests_require=['nose', 'mock'],
)
