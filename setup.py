from setuptools import setup, find_packages

# RQ 1.1.0 fixes the --disable-job-desc-logging option used by workers.
INSTALL_REQUIRES = ['rq>=1.1.0', 'osconf']

setup(
    name='autoworker',
    version='0.10.2',
    packages=find_packages(exclude=['spec']),
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
