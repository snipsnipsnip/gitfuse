=====
GitFS
=====

Easily mount git repositories as read-only file systems using FUSE.

Acknowledments
==============

GitFS was originally forked from
`py-gitfs<https://github.com/temoto/py-gitfs>`_ by Sergey Shepelev.

Usage
=====

::

    usage: gitfs [-h] <git_path> <mount_path>
    
    Mounts the contents of a git repository in read-only mode using FUSE.
    
    positional arguments:
      <git_path>    Path to git repository.
      <mount_path>  Path to mount point.
    
    optional arguments:
      -h, --help    show this help message and exit

License
=======

Please take a moment to review the license governing this software package as
specified in the ``LICENSE`` file.
