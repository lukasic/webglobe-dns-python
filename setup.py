from os.path import join as path_join, dirname
from setuptools import setup, find_packages

version = '0.1'

with open("README.md", "r") as f:
    long_description = f.read()

with open("requirements.txt", "r") as f:
    install_reqs = f.read().split()

setup(
    name='webglobedns',
    version=version,
    description=('Webglobe DNS Api Client.'),
    long_description=long_description,
    author='Lukas Kasic',
    author_email='src@lksc.sk',
    url='https://github.com/lukasic/webglobe-dns-python',
    packages=find_packages(),
    install_requires = install_reqs,
    keywords=['webglobe', "dns", "hosting"],
    classifiers=[
        'Development Status :: 1 - Planning',
        'License :: OSI Approved :: MIT',
        'Programming Language :: Python :: 3',
    ],
)