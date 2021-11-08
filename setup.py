import os
import setuptools

USERNAME = 'beasteers'
NAME = 'starstar'

import imp
version = imp.load_source('{}.__version__'.format(NAME), os.path.join(os.path.dirname(__file__), NAME, '__version__.py'))
version = version.__version__

setuptools.setup(
    name=NAME,
    version=version,
    description='Keyword argument tracing !!',
    long_description=open('README.md', encoding='utf-8').read().strip(),
    long_description_content_type='text/markdown',
    author='Bea Steers',
    author_email='bea.steers@gmail.com',
    url='https://github.com/{}/{}'.format(USERNAME, NAME),
    packages=setuptools.find_packages(),
    # entry_points={'console_scripts': ['{name}={name}:main'.format(name=NAME)]},
    install_requires=['docstring_parser'],
    extras_require={
        'test': ['pytest', 'pytest-cov']
    },
    license='MIT License',
    keywords='keyword kwargs kw star function arguments signature wrap trace')
