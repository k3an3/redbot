from pip.req import parse_requirements
from setuptools import setup

setup(
    name='redbot',
    version='0.0.1',
    packages=['redbot'],
    install_requires=parse_requirements('requirements.txt'),
    url='',
    scripts=['run.py'],
    license='MIT',
    author="Keane O'Kelley",
    author_email='kokelley@iastate.edu',
    description='Automated attack and traffic generation'
)
