#!/usr/bin/env python
# coding: utf-8

import argparse
import errno
import os
import stat
import fuse
import pygit2
import sys

from collections import namedtuple
from fuse import FuseOSError, FUSE, Operations, LoggingMixIn


arguments = argparse.ArgumentParser(
    description='Mounts the contents of a git repository in read-only mode using FUSE.'
)
arguments.add_argument('repo', metavar='repo', help='Path to git repository.')
arguments.add_argument('mount', metavar='mount', help='Path to mount point.')


StatT = namedtuple('StatT', ['st_mode', 'st_ino', 'st_dev', 'st_nlink', 'st_uid', 'st_gid', 'st_size', 'st_atime', 'st_mtime', 'st_ctime'])
"""
st_mode:  protection bits
st_ino:   inode number
st_dev:   device
st_nlink: number of hard links
st_uid:   user ID of owner
st_gid:   group ID of owner
st_size:  size of file, in bytes
st_atime: time of most recent access
st_mtime: time of most recent content modification
st_ctime: platform dependent; time of most recent metadata change on Unix,
          or the time of creation on Windows
"""
stat_zero = StatT(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)


def copy_stat(st, **kwargs):
    result = StatT(*st)
    return result._replace(**kwargs)


def git_tree_to_direntries(tree):
    for entry in tree:
        obj = entry.to_object()
        stat_type = stat.S_IFDIR if isinstance(obj, pygit2.Tree) else stat.S_IFREG
        yield fuse.Direntry(entry.name.encode('utf-8'), type=stat_type)


def git_tree_find_recursive(tree, path):
    parts = path.split('/')
    tree = reduce(lambda t, name: (t[name].to_object() if t is not None else None),
                  parts[:-1], tree)
    if tree is None:  # dir1
        return None
    entry = tree[parts[-1]]
    return entry


class GitFS(Operations, LoggingMixIn):
    def __init__(self, dir):
        dir = os.path.abspath(dir)
        dot_git = os.path.join(dir, '.git')

        self.dir = dot_git if os.path.exists(dot_git) else dir

        self.repo = pygit2.Repository(self.git_dir)

    def getattr(self, path, fh=None):
        stat_repo = os.lstat(self.repo.path)
        default_stat_dir = copy_stat(stat_repo, st_ino=0,
                                     # This is read-only file system
                                     st_mode=stat_repo.st_mode & ~0222)

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
        refs = [s[4:].encode('utf-8') for s in self.repo.listall_references() if s.startswith("refs/")]

        # Special case
        if path == "/":
            return list(frozenset([parts[1] for parts in [ref.split("/") for ref in refs] if len(parts) > 0]))

        # Path is a strict parent of a ref? Example: /remotes
        path_len_1 = len(path) + 1
        matching = [ref for ref in refs if ref.startswith(path + "/")]
        if len(matching) > 0:
            children = frozenset([ref[path_len_1:].split("/", 1)[0] for ref in matching if len(ref) > path_len_1])
            return [fuse.Direntry(name, type=stat.S_IFDIR) for name in children]

        # Path is ref? Example: /heads/master
        if path in refs:
            ref = self.repo.lookup_reference("refs" + path)
            ref = ref.resolve()
            commit = self.repo[ref.oid]
            return list(git_tree_to_direntries(commit.tree))

        # Path is strict child of a ref? Example: /heads/master/dir1/subdir
        matching = [ref for ref in refs if path.startswith(ref + "/")]
        if len(matching) == 1:
            ref_name = matching[0]  # /heads/master
            ref = self.repo.lookup_reference("refs" + ref_name)
            commit = self.repo[ref.oid]
            file_path = path[len(ref_name) + 1:]  # dir1/subdir
            entry = git_tree_find_recursive(commit.tree, file_path)
            if entry is None:
                return -errno.ENOENT
            if entry.attributes & stat.S_IFDIR == stat.S_IFDIR:
                subtree = self.repo[entry.oid]
                return list(git_tree_to_direntries(subtree))

        log.debug(u"  Fallback")
        return []

    def open(self, path, flags):
        log.debug(u"open(%s, %s)", path, flags)

        if path.startswith("/."):
            return -errno.ENOENT

        if flags & os.O_RDONLY != os.O_RDONLY:
            return -errno.EACCES

    def read(self, path, size, offset):
        log.debug(u"read(%s, %s, %s)", path, size, offset)
        if path.startswith("/."):
            return -errno.ENOENT

        refs = [s[4:].encode('utf-8') for s in self.repo.listall_references() if s.startswith("refs/")]

        # Path is strict child of a ref? Example: /heads/master/README.txt
        matching = [ref for ref in refs if path.startswith(ref + "/")]
        if len(matching) == 1:
            ref_name = matching[0]  # /heads/master
            file_path = path[len(ref_name) + 1:]  # README.txt
            ref = self.repo.lookup_reference("refs" + ref_name)
            commit = self.repo[ref.oid]
            entry = git_tree_find_recursive(commit.tree, file_path)
            if entry is None:
                return -errno.ENOENT
            blob = entry.to_object()
            if offset == 0 and len(blob.data) <= size:
                return blob.data
            return blob.data[offset:offset + size]

        log.debug(u"  Fallback")
        return -errno.ENOENT


def main(arguments):
    server = GitFS(arguments.repo)
    server.flags = 0
    server.multithreaded = 0

    fuse_args = [arguments.mount, "-f"]
    if arguments.fuse:
        fuse_args += ["-o", arguments.fuse]
    server.parse(fuse_args, errex=1)

    if server.fuse_args.mount_expected():
        if not os.path.exists(server.fuse_args.mountpoint):
            print >>sys.stderr, u"Mount point '{0}' does not exist.".format(server.fuse_args.mountpoint)
            exit(2)
    return server.main()


if __name__ == "__main__":
    self_pid = os.getpid()
    signal.signal(signal.SIGINT, lambda *a, **kw: os.kill(self_pid, signal.SIGTERM))
    logging.basicConfig(level=logging.WARN)
    log = logging.getLogger("gitfs")
    try:
        exit(main(arguments.parse_args()))
    except KeyboardInterrupt:
        exit(1)
