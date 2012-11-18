#!/usr/bin/env python
# coding: utf-8

import argparse
import errno
import logging
import os
import pygit2
import stat
import sys

from collections import namedtuple
from fuse import FuseOSError, FUSE, Operations, LoggingMixIn


# st_mode:  protection bits
# st_ino:   inode number
# st_dev:   device
# st_nlink: number of hard links
# st_uid:   user ID of owner
# st_gid:   group ID of owner
# st_size:  size of file, in bytes
# st_atime: time of most recent access
# st_mtime: time of most recent content modification
# st_ctime: platform dependent; time of most recent metadata change on Unix, or
#           the time of creation on Windows
Stat = namedtuple(
    'Stat',
    [
        'st_mode',
        'st_ino',
        'st_dev',
        'st_nlink',
        'st_uid',
        'st_gid',
        'st_size',
        'st_atime',
        'st_mtime',
        'st_ctime',
    ]
)

stat_zero = Stat(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)


def copy_stat(st, **kwargs):
    result = Stat(*st)

    result = result._replace(**kwargs)
    result = result._replace(
        st_ino=0,
        # Remove any write bits from st_mode
        st_mode=result.st_mode & ~0222,
    )

    return result._asdict()


def git_tree_to_direntries(tree):
    for entry in tree:
        yield entry.name.encode('utf-8')


def git_tree_find_recursive(tree, path):
    parts = path.split('/')

    tree = reduce(
        lambda t, name: (t[name].to_object() if t is not None else None),
        parts[:-1],
        tree,
    )

    if tree is None:  # dir1
        return None

    entry = tree[parts[-1]]
    return entry


class GitFS(Operations, LoggingMixIn):
    class GitFSError(Exception):
        pass

    def __init__(self, base_path):
        base_path = os.path.abspath(base_path)
        git_path = os.path.join(base_path, '.git')

        if os.path.exists(git_path):
            self.repo = pygit2.Repository(git_path)
        elif os.path.exists(base_path):
            self.repo = pygit2.Repository(base_path)
        else:
            raise self.GitFSError(
                'Path \'{0}\' does not point to a valid repository'.format(base_path)
            )

    def getattr(self, path, fh=None):
        if path.startswith('/.'):
            raise FuseOSError(errno.ENOENT)

        repo_stat = os.lstat(self.repo.path)
        default_stat = copy_stat(repo_stat)

        if path == '/':
            return default_stat

        refs = [
            r[4:].encode('utf-8')
            for r
            in self.repo.listall_references()
            if r.startswith('refs/')
        ]

        # If there are any refs that start with this path, return default stat.
        # This would mean anything 'above' a ref.
        if filter(lambda r: r.startswith(path), refs):
            return default_stat

        # Look for a ref that this path would be a child of.  This would mean
        # anything 'under' a ref.
        matching = filter(lambda r: path.startswith(r + '/'), refs)
        # If a single parent ref is found...
        if len(matching) == 1:
            # Get ref commit object
            ref_name = matching[0]  # /heads/master
            ref = self.repo.lookup_reference('refs' + ref_name)
            commit = self.repo[ref.oid]

            # Get path of file under ref
            file_path = path[len(ref_name) + 1:]  # dir/subdir/README.txt

            # Get the tree entry for the file path
            # TODO: In light of new understanding, revisit git_tree_find_recursive
            entry = git_tree_find_recursive(commit.tree, file_path)

            # If not found, no ent
            if entry is None:
                raise FuseOSError(errno.ENOENT)

            # If entry is directory, return default stat
            if entry.attributes & stat.S_IFDIR == stat.S_IFDIR:
                return default_stat

            # If stand-alone file, set extra file stats and return
            blob = self.repo[entry.oid]
            size = len(blob.data)
            return copy_stat(repo_stat, st_size=size, st_mode=entry.attributes)
        # If, for some reason, more than one ref is found...
        elif len(matching) > 1:
            raise self.GitFSError(
                'Duplicate refs matching path in stat query: {0}'.format(matching)
            )

        # Fallback to no ent
        raise FuseOSError(errno.ENOENT)

    # def readdir(self, path, offset):
    #     refs = [s[4:].encode('utf-8') for s in self.repo.listall_references() if s.startswith('refs/')]

    #     # Special case
    #     if path == '/':
    #         return list(frozenset([parts[1] for parts in [ref.split('/') for ref in refs] if len(parts) > 0]))

    #     # Path is a strict parent of a ref? Example: /remotes
    #     path_len_1 = len(path) + 1
    #     matching = [ref for ref in refs if ref.startswith(path + '/')]
    #     if len(matching) > 0:
    #         return list(frozenset([ref[path_len_1:].split('/', 1)[0] for ref in matching if len(ref) > path_len_1]))

    #     # Path is ref? Example: /heads/master
    #     if path in refs:
    #         ref = self.repo.lookup_reference('refs' + path)
    #         ref = ref.resolve()
    #         commit = self.repo[ref.oid]
    #         return list(git_tree_to_direntries(commit.tree))

    #     # Path is strict child of a ref? Example: /heads/master/dir1/subdir
    #     matching = [ref for ref in refs if path.startswith(ref + '/')]
    #     if len(matching) == 1:
    #         ref_name = matching[0]  # /heads/master
    #         ref = self.repo.lookup_reference('refs' + ref_name)
    #         commit = self.repo[ref.oid]
    #         file_path = path[len(ref_name) + 1:]  # dir1/subdir
    #         entry = git_tree_find_recursive(commit.tree, file_path)
    #         if entry is None:
    #             raise FuseOSError(errno.ENOENT)
    #         if entry.attributes & stat.S_IFDIR == stat.S_IFDIR:
    #             subtree = self.repo[entry.oid]
    #             return list(git_tree_to_direntries(subtree))

    #     return []

    # def open(self, path, flags):
    #     if path.startswith('/.'):
    #         return FuseOSError(errno.ENOENT)

    #     if flags & os.O_RDONLY != os.O_RDONLY:
    #         return FuseOSError(errno.EACCES)

    # def read(self, path, size, offset):
    #     if path.startswith('/.'):
    #         return FuseOSError(errno.ENOENT)

    #     refs = [s[4:].encode('utf-8') for s in self.repo.listall_references() if s.startswith('refs/')]

    #     # Path is strict child of a ref? Example: /heads/master/README.txt
    #     matching = [ref for ref in refs if path.startswith(ref + '/')]
    #     if len(matching) == 1:
    #         ref_name = matching[0]  # /heads/master
    #         file_path = path[len(ref_name) + 1:]  # README.txt
    #         ref = self.repo.lookup_reference('refs' + ref_name)
    #         commit = self.repo[ref.oid]
    #         entry = git_tree_find_recursive(commit.tree, file_path)
    #         if entry is None:
    #             return FuseOSError(errno.ENOENT)
    #         blob = entry.to_object()
    #         if offset == 0 and len(blob.data) <= size:
    #             return blob.data
    #         return blob.data[offset:offset + size]

    #     return FuseOSError(errno.ENOENT)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Mounts the contents of a git repository in read-only mode using FUSE.'
    )
    parser.add_argument('git_path', metavar='<git_path>', help='Path to git repository.')
    parser.add_argument('mount_path', metavar='<mount_path>', help='Path to mount point.')

    if len(sys.argv) != 3:
        parser.print_help()
        sys.exit(0)

    logging.getLogger().setLevel(logging.DEBUG)

    args = parser.parse_args()
    fuse = FUSE(GitFS(args.git_path), args.mount_path, foreground=True, debug=True)
