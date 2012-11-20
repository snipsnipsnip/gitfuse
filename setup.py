from setuptools import setup


setup(
    name='gitfuse',
    version='1.0',
    description='Easily mount git repositories as read-only file systems using FUSE.',
    url='https://github.com/davesque/gitfuse',
    author='David Sanders',
    author_email='davesque@gmail.com',
    license='MIT',
    packages=['gitfuse'],
    install_requires=[
        'argparse==1.2.1',
        'fusepy==2.0.1',
    ],
    dependency_links=[
        'https://github.com/libgit2/pygit2/tarball/af1c6ca10d7108f22b081436445901284ed9ef13#egg=pygit-0.17.3'
    ],
    zip_safe=False,
)
