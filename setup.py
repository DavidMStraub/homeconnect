from setuptools import setup, find_packages


with open('README.md') as f:
    LONG_DESCRIPTION = f.read()

setup(name='homeconnect',
      version='0.5',
      author='David M. Straub',
      author_email='david.straub@tum.de',
      url='https://github.com/DavidMStraub/homeconnect',
      description='Python client for the BSH Home Connect REST API',
      long_description=LONG_DESCRIPTION,
      long_description_content_type='text/markdown',
      license='MIT',
      packages=find_packages(),
      install_requires=['requests', 'requests_oauthlib'],
      extras_require={
            'testing': ['nose',],
      },
    )
