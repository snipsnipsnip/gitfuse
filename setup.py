from setuptools import setup


def readme():
    with open('README.rst') as f:
        return f.read()


setup(name='gitfuse',
      version='0.9',
      description='Easily mount git repositories as read-only file systems using FUSE.',
      long_description=readme(),
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3',
          'Topic :: System :: Filesystems',
      ],
      keywords='git fs read only file system fuse',
      url='https://github.com/davesque/gitfuse',
      author='David Sanders',
      author_email='davesque@gmail.com',
      license='MIT',
      packages=['gitfuse'],
      scripts=['bin/gitfuse'],
      install_requires=[
          'argparse==1.2.1',
          'pygit2==0.28.2',
          'fusepy==3.0.1',
      ],
      zip_safe=False)
