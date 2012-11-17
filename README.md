# GitFS

Easily mount git repositories as read-only file systems
using FUSE.

## Acknowledments

GitFS was originally forked from [py-gitfs](https://github.com/temoto/py-gitfs)
by Sergey Shepelev.

## Usage

    usage: gitfs [-h] <git_path> <mount_path>
    
    Mounts the contents of a git repository in read-only mode using FUSE.
    
    positional arguments:
      <git_path>    Path to git repository.
      <mount_path>  Path to mount point.
    
    optional arguments:
      -h, --help    show this help message and exit
