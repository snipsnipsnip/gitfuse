=======
GitFuse
=======

Easily mount git repositories as read-only file systems using FUSE.

Acknowledments
==============

GitFuse was originally forked from py-gitfs_ by Sergey Shepelev.

Usage
=====

::

    usage: gitfuse [-h] <git_path> <mount_path>

    Mounts the contents of a git repository in read-only mode using FUSE.

    positional arguments:
      <git_path>    Path to git repository.
      <mount_path>  Path to mount point.

    optional arguments:
      -h, --help    show this help message and exit

Known issues
============

1. When running `gitfuse` from the command line, the user sees an error similar
   to the following:

   ::

       ImportError: libgit2.so.0: cannot open shared object file: No such file
       or directory

   This happens when the libgit2 library files cannot be found by the pygit2
   python module.  There are two ways to fix this problem that I'm aware of:

        - By manually installing pygit2 with the following command:

          ::

              export LD_RUN_PATH=/usr/local/lib && python setup.py install

License
=======

Please take a moment to review the license governing this software package as
specified in the ``LICENSE`` file.

.. _py-gitfs: https://github.com/temoto/py-gitfs
