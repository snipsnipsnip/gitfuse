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
          'Programming Language :: Python :: 2.6',
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
          'fusepy==2.0.1',
      ],
      dependency_links=[
          'https://github.com/libgit2/pygit2/tarball/af1c6ca10d7108f22b081436445901284ed9ef13#egg=pygit-0.17.3'
      ],
      zip_safe=False)
