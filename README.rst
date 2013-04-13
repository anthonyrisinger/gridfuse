GridFUSE: [r/w] python virtual filesystem a la GridFS/FUSE
==========================================================

complete enough to run my full development stack without error and mostly
without *human* noticeable performance loss... alas, ``gridfuse.py`` != fast

Requirements
------------

- python 2.6+ (includes 3.x)
- pymongo_
- fusepy_

Performance
-----------

...near 100% arbitrary and non-scientific!

===================================== ======== ====== ===========
command                               time (s) inodes total (MiB)
------------------------------------- -------- ------ -----------
``# cp -a devel/venv mnt/devel/venv`` **120**  ~6200  815
------------------------------------- -------- ------ -----------
``# cp -a prod.sql mnt/prod.sql``     **20**   1      448
------------------------------------- -------- ------ -----------
``# tree -a mnt/``                    **18**   ~6200
------------------------------------- -------- ------ -----------
``# tree mnt/``                       **6**    ~2300
===================================== ======== ====== ===========

Caveats
-------

- ``planned`` nothing is **EVER** [physically] deleted, only logically
- ``???????`` hard links unsupported (i think possible, maybe even easy)
- ``planned`` xattrs unsupported
- ``planned`` does not check/enforce permissions well (...at all)
- ``planned`` doesnt create proper indexes (...or any)
- ``planned`` inefficient architecture...

.. note:: rather late... i discovered GridFS **does not** update filedata!
          instead, it "overwrites" files by creating a 100% new file with
          the same ``filename``; an unintended [but harmless] side-effect of
          the current impl (due to specific "paranoid" access patterns, wrt
          file creation) may generate 1-2 hidden/older, zero-byte revisions.

Interface
---------

.. code:: shell-session

    [me@you gridfuse]$ python gridfuse.py --help
    usage: gridfuse.py [-h] [-f] [-s] [-v] [--node CONNECTION] [--db DATABASE]
                       [--coll COLLECTION]
                       DIR

    positional arguments:
      DIR                mountpoint

    optional arguments:
      -h, --help         show this help message and exit
      -f, --foreground   [FUSE] do not daemonize
      -s, --nothreads    [FUSE] do not use multiple threads
      -v, --verbose      increase output verbosity (repeatable)
      --node CONNECTION  connection: [mongodb://]HOST[/db[/coll]] (repeatable)
      --db DATABASE      force specified database
      --coll COLLECTION  force specified collection

Example
-------

.. code:: shell-session

    [me@you gridfuse]$ mkdir -p mnt/
    [me@you gridfuse]$ ls -n mnt/
    total 0
    [me@you gridfuse]$ python gridfuse.py mnt/
    [me@you gridfuse]$ cd mnt/
    [me@you gridfuse]$ mkdir -p sub/dir
    [me@you gridfuse]$ ln -s sub/dir/dup sym
    [me@you gridfuse]$ ls -n
    total 0
    lrwxrwxrwx 1 1000 100 11 Apr 13 09:11 sym -> sub/dir/dup
    drwxr-xr-x 1 1000 100  0 Apr 13 09:11 sub/
    [me@you gridfuse]$ cat sym
    cat: sym: No such file or directory
    [me@you gridfuse]$ echo helloworld > sub/reg
    [me@you gridfuse]$ cat sub/reg
    helloworld
    [me@you gridfuse]$ cp sub/reg sub/dir/dup
    [me@you gridfuse]$ md5sum sym sub/reg sub/dir/dup
    d73b04b0e696b0945283defa3eee4538  sym
    d73b04b0e696b0945283defa3eee4538  sub/reg
    d73b04b0e696b0945283defa3eee4538  sub/dir/dup
    [me@you gridfuse]$ tree -F --charset ascii --noreport
    .
    |-- sub/
    |   |-- dir/
    |   |   `-- dup
    |   `-- reg
    `-- sym -> sub/dir/dup

.. _pymongo: https://pypi.python.org/pypi/pymongo/
.. _fusepy: https://pypi.python.org/pypi/fusepy/

`MIT LICENSED <http://opensource.org/licenses/mit-license.html>`_
