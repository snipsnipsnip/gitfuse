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

1. When running `gitfuse` from the command line, the user sees the following
   error:

   ::

       ImportError: libgit2.so.0: cannot open shared object file: No such file
       or directory

   This happens when the libgit2 library files cannot be found by the dynamic
   linker.  There are two ways to fix this problem that I'm aware of:

        - By manually installing pygit2 after setting the LD_RUN_PATH
          environment variable:

          ::

              export LD_RUN_PATH=/usr/local/lib && python setup.py install

        - By running gitfuse after updating the LD_LIBRARY_PATH environment
          variable:

          ::

              export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib && gitfuse

    The first of the two methods is the preferred one since it is a permanent
    fix for the problem on a particular system.  Do not modify the
    LD_LIBRARY_PATH environment variable as a blanket fix in your .bashrc.
    Reasons to avoid this can be found in this_ stackoverflow post.

License
=======

Please take a moment to review the license governing this software package as
specified in the ``LICENSE`` file.

.. _py-gitfs: https://github.com/temoto/py-gitfs
.. _this: http://stackoverflow.com/questions/1099981/why-cant-python-find-shared-objects-that-are-in-directories-in-sys-path
