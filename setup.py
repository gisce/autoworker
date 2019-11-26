from setuptools import setup, find_packages

INSTALL_REQUIRES = ['rq>=0.10.0', 'osconf']

setup(
    name='autoworker',
    version='0.7.2',
    packages=find_packages(),
    url='https://github.com/gisce/autoworker',
    license='MIT',
    author='GISCE-TI, S.L.',
    author_email='devel@gisce.net',
    install_requires=INSTALL_REQUIRES,
    description='Start Python RQ Workers automatically',
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5'
    ]
)
