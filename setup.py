import os
from shutil import copyfile

from setuptools import setup, find_packages
from setuptools.command.install import install


class CustomInstallCommand(install):
    def run(self):
        if os.path.isdir('/etc/systemd/system'):
            path = os.path.dirname(os.path.realpath(__file__))
            for file in os.listdir(os.path.join(path, 'scripts')):
                if os.path.isfile(os.path.join('scripts', file)) and file.endswith('.service'):
                    copyfile(os.path.join('scripts', file), os.path.join('/etc/systemd/system', file))
        super().run()


with open('requirements.txt') as f:
    required = [line for line in f.read().splitlines() if not line.startswith('git')]
    gitdeps = [line for line in f.read().splitlines() if line.startswith('git')]

setup(
    name='redbot',
    version='0.0.1',
    packages=find_packages(),
    install_requires=required,
    dependency_links=gitdeps,
    url='',
    license='MIT',
    author="Keane O'Kelley",
    author_email='kokelley@iastate.edu',
    description='Automated attack and traffic generation',
    scripts=['redbot-web', 'redbot-celery', 'redbot-celerybeat'],
    cmdclass={'install': CustomInstallCommand}
)
