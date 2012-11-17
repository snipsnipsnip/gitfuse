#!/usr/bin/env python
# coding: utf-8

import argparse
import errno
import os
import stat
import pygit2
import sys
import logging

from collections import namedtuple
from fuse import FuseOSError, FUSE, Operations, LoggingMixIn


StatT = namedtuple('StatT', ['st_mode', 'st_ino', 'st_dev', 'st_nlink', 'st_uid', 'st_gid', 'st_size', 'st_atime', 'st_mtime', 'st_ctime'])

##|  st_mode:  protection bits
##|  st_ino:   inode number
##|  st_dev:   device
##|  st_nlink: number of hard links
##|  st_uid:   user ID of owner
##|  st_gid:   group ID of owner
##|  st_size:  size of file, in bytes
##|  st_atime: time of most recent access
##|  st_mtime: time of most recent content modification
##|  st_ctime: platform dependent; time of most recent metadata change on Unix,
##|            or the time of creation on Windows

stat_zero = StatT(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)


def copy_stat(st, **kwargs):
    result = StatT(*st)
    return result._replace(**kwargs)


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

    def __init__(self, git_path):
        git_path = os.path.abspath(git_path)
        dot_git = os.path.join(git_path, '.git')

        if not (os.path.exists(git_path) or os.path.exists(dot_git)):
            raise self.GitFSError('Neither \'{0}\' or \'{1}\' exists'.format(
                git_path,
                dot_git,
            ))

        self.repo = pygit2.Repository(
            dot_git if os.path.exists(dot_git) else git_path
        )

    def getattr(self, path, fh=None):
        stat_repo = os.lstat(self.repo.path)

        default_stat_dir = copy_stat(
            stat_repo, st_ino=0,
            # This is read-only file system
            st_mode=stat_repo.st_mode & ~0222,
        )

        if path == '/':
            return default_stat_dir

        if path.startswith('/.'):
            raise FuseOSError(errno.ENOENT)

        refs = [s[4:].encode('utf-8') for s in self.repo.listall_references() if s.startswith('refs/')]

        # Path is ref or parent of a ref? Examples: /heads/master, /remotes/origin
        matching = [ref for ref in refs if ref.startswith(path)]
        if len(matching) > 0:
            return default_stat_dir

        # Path is strict child of a ref? Example: /heads/master/dir/subdir/README.txt
        matching = [ref for ref in refs if path.startswith(ref + '/')]
        if len(matching) == 1:
            ref_name = matching[0]  # /heads/master
            ref = self.repo.lookup_reference('refs' + ref_name)
            commit = self.repo[ref.oid]
            file_path = path[len(ref_name) + 1:]  # dir/subdir/README.txt
            entry = git_tree_find_recursive(commit.tree, file_path)
            if entry is None:
                raise FuseOSError(errno.ENOENT)
            if entry.attributes & stat.S_IFDIR == stat.S_IFDIR:
                return default_stat_dir

            blob = self.repo[entry.oid]
            size = len(blob.data)

            # This is read-only file system
            mode = entry.attributes & ~0222
            return copy_stat(stat_repo, st_ino=0, st_size=size, st_mode=mode)

        raise FuseOSError(errno.ENOENT)

    def readdir(self, path, offset):
        refs = [s[4:].encode('utf-8') for s in self.repo.listall_references() if s.startswith('refs/')]

        # Special case
        if path == '/':
            return list(frozenset([parts[1] for parts in [ref.split('/') for ref in refs] if len(parts) > 0]))

        # Path is a strict parent of a ref? Example: /remotes
        path_len_1 = len(path) + 1
        matching = [ref for ref in refs if ref.startswith(path + '/')]
        if len(matching) > 0:
            return list(frozenset([ref[path_len_1:].split('/', 1)[0] for ref in matching if len(ref) > path_len_1]))

        # Path is ref? Example: /heads/master
        if path in refs:
            ref = self.repo.lookup_reference('refs' + path)
            ref = ref.resolve()
            commit = self.repo[ref.oid]
            return list(git_tree_to_direntries(commit.tree))

        # Path is strict child of a ref? Example: /heads/master/dir1/subdir
        matching = [ref for ref in refs if path.startswith(ref + '/')]
        if len(matching) == 1:
            ref_name = matching[0]  # /heads/master
            ref = self.repo.lookup_reference('refs' + ref_name)
            commit = self.repo[ref.oid]
            file_path = path[len(ref_name) + 1:]  # dir1/subdir
            entry = git_tree_find_recursive(commit.tree, file_path)
            if entry is None:
                raise FuseOSError(errno.ENOENT)
            if entry.attributes & stat.S_IFDIR == stat.S_IFDIR:
                subtree = self.repo[entry.oid]
                return list(git_tree_to_direntries(subtree))

        return []

    def open(self, path, flags):
        if path.startswith('/.'):
            return FuseOSError(errno.ENOENT)

        if flags & os.O_RDONLY != os.O_RDONLY:
            return FuseOSError(errno.EACCES)

    def read(self, path, size, offset):
        if path.startswith('/.'):
            return FuseOSError(errno.ENOENT)

        refs = [s[4:].encode('utf-8') for s in self.repo.listall_references() if s.startswith('refs/')]

        # Path is strict child of a ref? Example: /heads/master/README.txt
        matching = [ref for ref in refs if path.startswith(ref + '/')]
        if len(matching) == 1:
            ref_name = matching[0]  # /heads/master
            file_path = path[len(ref_name) + 1:]  # README.txt
            ref = self.repo.lookup_reference('refs' + ref_name)
            commit = self.repo[ref.oid]
            entry = git_tree_find_recursive(commit.tree, file_path)
            if entry is None:
                return FuseOSError(errno.ENOENT)
            blob = entry.to_object()
            if offset == 0 and len(blob.data) <= size:
                return blob.data
            return blob.data[offset:offset + size]

        return FuseOSError(errno.ENOENT)


if __name__ == '__main__':
    arguments = argparse.ArgumentParser(
        description='Mounts the contents of a git repository in read-only mode using FUSE.'
    )
    arguments.add_argument('git_path', metavar='<git_path>', help='Path to git repository.')
    arguments.add_argument('mount_path', metavar='<mount_path>', help='Path to mount point.')

    if len(sys.argv) != 3:
        arguments.print_help()
        sys.exit(0)

    logging.getLogger().setLevel(logging.DEBUG)
    # fuse = FUSE(GitFS(arguments.git_path), arguments.mount_path, foreground=True)
