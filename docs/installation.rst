Installation
============

Prerequisites
-------------

To install the ``madmom`` package, you must have either Python 2.7 or Python
3.3 or newer and the following packages installed:

- `numpy <http://www.numpy.org>`_
- `scipy <http://www.scipy.org>`_
- `cython <http://www.cython.org>`_
- `nose <https://github.com/nose-devs/nose>`_ (to run the tests)

If you need support for audio files other than ``.wav`` with a sample rate of
44.1kHz and 16 bit depth, you need ``ffmpeg`` (``avconv`` on Ubuntu Linux has
some decoding bugs, so we advise not to use it!).

Please refer to the ``requirements.txt`` file for the minimum required versions
and make sure that these modules are up to date, otherwise it can result in
unexpected errors or false computations!

.. _install_from_package:

Install from package
--------------------

If you intend to change anything within the `madmom` package, please follow the
steps in :ref:`the next section <install_from_source>`.

The instructions given here should be used if you just want to install the
package (e.g. to run the bundled programs).

The easiest way to install the package is via ``pip`` from the `PyPI (Python
Package Index) <https://pypi.python.org/pypi>`_::

    pip install madmom

This includes the latest code and trained models and will install all
dependencies automatically. It will also install the executable scripts to a
common place (e.g. ``/usr/local/bin``) which should be in your ``$PATH``
already. ``pip`` will output the install location.

You might need higher privileges (use su or sudo) to install the package, model
files and scripts globally. Alternatively you can install the package locally
(i.e. only for you) by adding the ``--user`` argument::

    pip install --user madmom

Depending on your platform, the scripts will be copied to a folder which
might not be included in your ``$PATH`` (e.g. ``~/Library/Python/2.7/bin``
on Mac OS X or ``~/.local/bin`` on Ubuntu Linux), so please call the scripts
directly or add their path to your ``$PATH`` environment variable:

    export PATH='path/to/scripts':$PATH

.. _install_from_source:

Install from source
-------------------

If you plan to use the package as a developer, clone the Git repository::

    git clone https://github.com/CPJKU/madmom.git

Since the pre-trained model/data files are not included in this repository but
rather added as a Git submodule, you either have to clone the repo
recursively::

    git clone --recursive https://github.com/CPJKU/madmom.git

or init the submodule and fetch the data manually::

    cd /path/to/madmom
    git submodule update --init --remote

You can then either include the package directory in your ``$PYTHONPATH``, or
you can simply install the package in development mode::

    python setup.py develop --user

If you change any ``.pyx`` or ``.pxd`` files, you have to (re-)compile the
modules with Cython. To do so, please run the above command again or::

    python setup.py build_ext --inplace

To run the included tests::

    python setup.py test

Executable programs
-------------------

The package includes executable programs in the ``/bin`` folder. These are
standalone reference implementations of the algorithms contained in the
package. If you just want to try/use these programs, please follow the
:ref:`instruction to install from a package <install_from_package>`.

All scripts can be run in different modes: in ``single`` file mode to process
a single audio file and write the output to STDOUT or the given output file::

    SuperFlux single [-o OUTFILE] INFILE

If multiple audio files should be processed, the scripts can also be run in
``batch`` mode to write the outputs to files with the given suffix::

    SuperFlux batch [--o OUTPUT_DIR] [-s OUTPUT_SUFFIX] LIST OF INPUT FILES

If no output directory is given, the program writes the output files to same
location as the audio files.

The ``pickle`` mode can be used to store the used parameters to be able to
exactly reproduce experiments.
