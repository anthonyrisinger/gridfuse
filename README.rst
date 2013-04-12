needs... pymongo, fusepy... docs may [or may not] improve :/

ex.::

    # mkdir mnt
    # python2 gridfuse.py mnt
    # ls -l mnt
      total 0
    # mkdir -p mnt/path/to/nowhere
    # echo hithere > mnt/guy
    # cat mnt/guy
      hithere
    # cp mnt/guy mnt/path/to/nowhere/gal
    # md5sum mnt/guy mnt/path/to/nowhere/gal
      f8a2c6169117fbbee392bdd8f9cb623b  mnt/guy
      f8a2c6169117fbbee392bdd8f9cb623b  mnt/path/to/nowhere/gal
    # tree --noreport mnt
      mnt/
      |-- guy
      `-- path
          `-- to
              `-- nowhere
                  `-- gal

LICENSE BSD
