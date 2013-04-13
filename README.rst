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

- **[temp]** nothing is **EVER** [physically] deleted
- **[????]** hard links unsupported (i think possible, maybe even easy)
- **[temp]** does not check/enforce permissions well (...at all)
- **[temp]** doesnt create proper indexes (...or any)
- **[temp]** inefficient architecture...

.. note:: rather late... i discovered GridFS **does not** update filedata!
          instead, it "overwrites" files by creating a 100% new file with
          the same ``filename``; an unintended [but harmless] side-effect of
          the current impl (due to specific "paranoid" access patterns, wrt
          file creation) may generate 1-2 hidden/older, zero-byte revisions.

Interface
---------

``python gridfuse.py --help``::

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

try this at home kids! ::

    # ls mnt
      ls: cannot access mnt: No such file or directory
    # mkdir -p mnt/path/to/nowhere
    # python gridfuse.py mnt
    # ls -l mnt
      total 0
    # echo hithere > mnt/guy
    # cat mnt/guy
      hithere
    # cp mnt/guy mnt/path/to/nowhere
    # md5sum mnt/guy mnt/path/to/nowhere/guy
      f8a2c6169117fbbee392bdd8f9cb623b  mnt/guy
      f8a2c6169117fbbee392bdd8f9cb623b  mnt/path/to/nowhere/guy
    # tree --noreport mnt
      mnt/
      |-- guy
      `-- path
          `-- to
              `-- nowhere
                  `-- guy


.. _pymongo: https://pypi.python.org/pypi/pymongo/
.. _fusepy: https://pypi.python.org/pypi/fusepy/

`MIT LICENSED <http://opensource.org/licenses/mit-license.html>`_
