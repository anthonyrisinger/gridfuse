#!/usr/bin/env python

try:
    long
except NameError:
    basestring = str
    long = int

try:
    from urllib.parse import urlsplit, urlunsplit
except ImportError:
    from urlparse import urlsplit, urlunsplit

import sys
from sys import argv
import fuse
from fuse import FuseOSError, LoggingMixIn, Operations, fuse_get_context
from pymongo import Connection
from gridfs import GridFS, GridIn, GridOut
import os, stat, time

from errno import *
from stat import *

from bson.code import Code
from itertools import count, chain
from heapq import heappush, heappop

from os import path as pth

from pprint import pformat as pf, pprint as pp

def _fi_repr(self):
    return '<%s.%s: %s>' % (
            __name__,
            self.__class__.__name__,
            '\n\t'.join([
                ('%s=%r' % (x[0], getattr(self, x[0])))
                for x in self._fields_
                ]))

if hasattr(_fi_repr, 'func_name'):
    import types
    _fi_repr = types.MethodType(
            _fi_repr,
            None,
            fuse.fuse_file_info,
            )

fuse.fuse_file_info.__repr__ = _fi_repr



class GridFUSE(Operations):

    DEFAULT = ('mongodb://127.0.0.1/gridfs/fs',)
    FMODE = (stat.S_IRWXU|stat.S_IROTH|stat.S_IRGRP)^stat.S_IRUSR
    DMODE = FMODE|stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH
    ST = ({
        'st_mode': stat.S_IRWXU|stat.S_IRWXG|stat.S_IRWXO,
        'st_ino': 0,
        'st_dev': 0,
        'st_nlink': 1,
        'st_uid': os.geteuid(),
        'st_gid': os.getegid(),
        'st_size': 0,
        'st_atime': 0,
        'st_mtime': 0,
        'st_ctime': 0,
        })

    def __repr__(self):
        return '<%s.%s: %s>' % (
                __name__,
                self.__class__.__name__,
                ' '.join([
                    ('%s=%r' % x) for x in [
                        ('fs', self.fs),
                        ]]))

    def __init__(self, nodes=None, db=None, coll=None, *args, **kwds):
        super(GridFUSE, self).__init__()
        nodes = nodes or GridFUSE.DEFAULT
        if isinstance(nodes, basestring):
            nodes = [nodes]
        cluster = list()
        for node in nodes:
            uri = urlsplit(node)
            if not uri.scheme:
                cluster.append(node)
                continue
            if uri.scheme != 'mongodb':
                raise TypeError('invalid uri.scheme: %r' % uri.scheme)
            node_db, _, node_coll = uri.path.strip('/').partition('/')
            if db is None and node_db:
                db = node_db
            if coll is None and node_coll:
                coll = node_coll.replace('/', '.')
            cluster.append(urlunsplit((
                uri.scheme,
                uri.netloc,
                node_db,
                uri.query,
                uri.fragment,
                )))
        if not db or not coll:
            raise TypeError('undefined db and/or root collection')
        conn = self.conn = Connection(cluster)
        self.debug = bool(kwds.pop('debug', False))
        self.gfs = GridFS(conn[db], collection=coll)
        self.fs = conn[db][coll]
        self._ctx = Context(self)
        if not self.gfs.exists(filename=''):
            self.mkdir()

    def __call__(self, op, path, *args):
        if not hasattr(self, op):
            raise FuseOSError(EFAULT)
        ret = getattr(self, op)(path.strip('/'), *args)
        if self.debug:
            self._debug(op, path, args, ret)
        return ret

    def _debug(self, op, path, args, ret):
        own = op in self.__class__.__dict__
        sys.stderr.write('%s:%s:%i/%i/%i\n' % (
            (op.upper(), own) + fuse_get_context()
            ))
        sys.stderr.write(':: %s\n' % path)
        if op not in ('read', 'write'):
            sys.stderr.write(':: %s\n' % pf(args))
            sys.stderr.write(':: %s\n' % pf(ret))
        sys.stderr.write('\n')
        sys.stderr.flush()

    def getattr(self, path, fh):
        spec = None
        if fh is not None:
            fh, spec = self._ctx.get(fh)
        elif self.gfs.exists(filename=path, visible=True):
            spec = self.gfs.get_last_version(path)

        if spec is None:
            raise FuseOSError(ENOENT)

        st = spec.stat.copy()
        st['st_size'] = spec.length
        return st

    def chmod(self, path, mode):
        self.fs.files.update(
                {'filename': path, 'visible': True},
                {'$set': {'stat.st_mode': mode}},
                upsert=False,
                multi=False,
                )

    def chown(self, path, uid, gid):
        self.fs.files.update(
                {'filename': path, 'visible': True},
                {'$set': {'stat.st_uid': uid, 'stat.st_gid': gid}},
                upsert=False,
                multi=False,
                )

    def _ent(self, path):
        if self.gfs.exists(filename=path, visible=True):
            raise FuseOSError(EEXIST)
        dirname = basename = None
        if path:
            dirname, basename = pth.split(path)
        now = time.time()
        st = self.ST.copy()
        st.update(st_ctime=now, st_mtime=now, st_atime=now)
        return self.gfs.new_file(
                filename=path,
                stat=st,
                dirname=dirname,
                visible=True,
                )

    def create(self, path, mode=FMODE, fi=None):
        with self._ent(path) as spec:
            spec._file['stat'].update(st_mode=mode|S_IFREG)
        file = spec._file
        file.pop('_id')
        fh, spec = self._ctx.acquire(GridIn(self.fs, **file))
        if fi is not None:
            fi.fh = fh
            return 0
        return fh

    def mkdir(self, path='', mode=DMODE):
        with self._ent(path) as spec:
            spec._file['stat'].update(st_mode=mode|S_IFDIR)
        return 0

    #TODO: impl?
    def link(self, path, source):
        raise FuseOSError(ENOTSUP)

    def symlink(self, path, source):
        with self._ent(path) as spec:
            spec._file['stat'].update(st_mode=0o0777|S_IFLNK)
            spec.write(str(source))
        return 0

    def readlink(self, path):
        spec = None
        if self.gfs.exists(filename=path, visible=True):
            spec = self.gfs.get_last_version(path)

        if spec is None:
            raise FuseOSError(ENOENT)
        elif not spec.stat['st_mode'] & S_IFLNK > 0:
            raise FuseOSError(EINVAL)

        return spec.read()

    def readdir(self, path, fh):
        spec = None
        if fh is not None:
            fh, spec = self._ctx.get(fh)
        elif self.gfs.exists(filename=path, visible=True):
            spec = self.gfs.get_last_version(path)

        if spec is None:
            raise FuseOSError(ENOENT)
        elif not spec.stat['st_mode'] & S_IFDIR > 0:
            raise FuseOSError(ENOTDIR)

        for rel in ('.', '..'):
            yield rel

        for sub in self.fs.files.find({
            'dirname': path,
            'visible': True,
            }).distinct('filename'):
            yield pth.basename(sub)

    def open(self, path, flags=None):
        #TODO: handle os.O_* flags?
        fh, spec = self._ctx.get(path)
        if hasattr(flags, 'fh'):
            flags.fh = fh
            return 0
        return fh

    opendir = open

    def release(self, path, fh):
        return self._ctx.release(fh)

    releasedir = release

    def read(self, path, size, offset, fh):
        spec = self.gfs.get_last_version(path)
        spec.seek(offset, os.SEEK_SET)
        return spec.read(size)

    def write(self, path, data, offset, fh):
        if fh is not None:
            fh = getattr(fh, 'fh', fh)
            fh, spec = self._ctx.get(fh)
        elif self.gfs.exists(filename=path, visible=True):
            fh, spec = self._ctx.acquire(path)

        if not hasattr(spec, 'write'):
            self.truncate(path, 0, fh=fh)
            spec = self._ctx._fd[fh]
        spec.write(data)

        return len(data)

    def unlink(self, path):
        if not path:
            #...cannot remove mountpoint
            raise FuseOSError(EBUSY)

        spec = self.gfs.get_last_version(path)
        if spec is None or not spec.visible:
            raise FuseOSError(ENOENT)

        self.fs.files.update(
                {'filename': path},
                {'$set': {'visible': False}},
                upsert=False,
                multi=True,
                )

        return 0

    rmdir = unlink

    def truncate(self, path, length, fh=None):
        if length != 0:
            raise FuseOSError(ENOTSUP)

        spec = None
        if fh is not None:
            fh = getattr(fh, 'fh', fh)
            fh, spec = self._ctx.get(fh)
        elif self.gfs.exists(filename=path, visible=True):
            spec = self.gfs.get_last_version(path)
        if spec is None:
            raise FuseOSError(EBADF)

        if hasattr(spec, 'write') and spec._chunk_number==0:
            spec._buffer.truncate(0)
            spec._buffer.seek(0)
            spec._position = 0
        else:
            #FIXME: this is terrible... whole class needs refactor
            fi = spec._file
            fi.pop('_id')
            with self.gfs.new_file(**fi) as zero:
                self.unlink(path)
            if fh:
                self._ctx.release(fh)
                self._ctx._fd[fh] = self.gfs.new_file(**fi)

        return 0


class Context(object):

    def __repr__(self):
        return '<%s.%s: %s>' % (
                __name__,
                self.__class__.__name__,
                ' '.join([
                    ('%s=%r' % x) for x in [
                        ('fd', self._fd.keys()),
                        ]]))

    def __init__(self, fs):
        self._fs = fs
        self._fd = dict()
        self._fh = list()
        self._new = count(10)

    def get(self, fh):
        spec = None
        if isinstance(fh, (int, long)):
            spec = self._fd.get(long(fh))
        elif isinstance(fh, basestring) or hasattr(fh, '_file'):
            fh, spec = self.acquire(fh)
        if spec is None:
            raise FuseOSError(EBADF)

        return fh, spec

    def acquire(self, path):
        fh = None
        while fh is None or fh in self._fd:
            try:
                fh = heappop(self._fh)
            except IndexError:
                fh = long(next(self._new))

        spec = None
        if hasattr(path, '_file'):
            spec = self._fd[fh] = path
        elif isinstance(path, basestring):
            spec = self._fd[fh] = self._fs.gfs.get_last_version(
                    path,
                    visible=True,
                    )
        if spec is None:
            raise FuseOSError(EBADF)

        return fh, spec

    def release(self, fh):
        fh = getattr(fh, 'fh', fh)
        if fh not in self._fd:
            raise FuseOSError(EBADF)
        self._fd.pop(fh).close()
        heappush(self._fh, fh)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
            '-f', '--foreground',
            action='store_true',
            default=False,
            help='[FUSE] do not daemonize',
            )
    parser.add_argument(
            '-s', '--nothreads',
            action='store_true',
            default=False,
            help='[FUSE] do not use multiple threads',
            )
    parser.add_argument(
            '-v', '--verbose',
            action='count',
            default=False,
            help='increase output verbosity',
            )
    parser.add_argument(
            '--node',
            metavar='CONNECTION',
            action='append',
            help='connection: [mongodb://]HOST[/db[/coll]] (repeatable)',
            )
    parser.add_argument(
            '--db',
            metavar='DATABASE',
            help='force specified database',
            )
    parser.add_argument(
            '--coll',
            metavar='COLLECTION',
            help='force specified collection',
            )
    parser.add_argument(
            'mountpoint',
            metavar='DIR',
            help='mountpoint',
            )
    o = parser.parse_args()
    o.verbose = min(o.verbose, 3)

    fuse = fuse.FUSE(
            GridFUSE(o.node, o.db, o.coll, debug=bool(o.verbose & 1)),
            o.mountpoint,
            raw_fi=True,
            foreground=o.foreground,
            debug=bool(o.verbose & 2),
            nothreads=o.nothreads,
            )
