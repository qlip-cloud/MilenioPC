from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in milenio_pc/__init__.py
from milenio_pc import __version__ as version

setup(
	name='milenio_pc',
	version=version,
	description='Load Milenio PC NC and FV file',
	author='Henderson Villegas',
	author_email='henderson.villegas@mentum.com.co',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
