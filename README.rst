******
FCMcmp
******

The goal of FCMcmp is to make it easy to analyze flow cytometry data from 
python.  The first challenge in analyzing flow cytometry data is working out 
which wells should be compared with each other.  For example, which wells are 
controls, which wells are replicates of each other, which wells contain the 
conditions you're interested in, etc.  This isn't usually too complicated for 
individual experiments, but if you want to write analysis scripts that you can 
use on all of your data, managing this metadata becomes a significant problem.

FCMcmp addresses this problem by defining a simple YAML file format that can 
associate wells and plates in pretty much any way you want.  When you ask 
FCMcmp to parse these files, it returns a list- and dictionary-based data 
structure that contains these associations, plus it automatically parses the 
raw FCS data into pandas data frames.

.. image:: https://img.shields.io/pypi/v/fcmcmp.svg
   :target: https://pypi.python.org/pypi/fcmcmp

.. image:: https://img.shields.io/pypi/pyversions/fcmcmp.svg
   :target: https://pypi.python.org/pypi/fcmcmp

.. image:: https://img.shields.io/travis/kalekundert/fcmcmp.svg
   :target: https://travis-ci.org/kalekundert/fcmcmp

.. image:: https://img.shields.io/coveralls/kalekundert/fcmcmp.svg
   :target: https://coveralls.io/github/kalekundert/fcmcmp?branch=master

Installation
============
``fcmcmp`` is available on PyPI::

   pip3 install fcmcmp

Only python>=3.4 is supported.

Quick Start
===========
I'll demonstrate using data you might export from running a 96-well plate on a 
BD LSRII, but the library should be pretty capable of handling any directory 
hierarchy::

   my_plate/
      96 Well - U bottom/
         Specimen_001_A1_A01_001.fcs
         Specimen_002_A2_A02_002.fcs
         Specimen_003_A3_A03_003.fcs
         ...

Loading the data
~~~~~~~~~~~~~~~~
First, we need to make a YAML metadata file describing the relationships 
between the wells on this plate::

    # my_plate.yml
   label: vaxadrin
   wells:
      without: [A1,A2,A3]
      with: [B1,B2,B3]
   ---
   label: vaxamaxx
   wells:
      without: [A1,A2,A3]
      with: [C1,C2,C3]

In this example, the name of the plate directory is inferred from the name of 
the YAML file.  You can also explicitly specify the path to the plate directory 
by adding the following header before the ``label``/``wells`` sections::

   plate: path/to/my_plate
   ---

You can even reference wells from multiple plates in one file::

   plates:
      foo: path/to/foo_plate
      bar: path/to/bar_plate
   ---
   label: vaxascab
   wells:
      without: [foo/A1, foo/A2, foo/A3]
      with: [bar/A1, bar/A2, bar/A3]

Note that the ``label`` and ``wells`` fields are required, but you can add, 
remove, or rename any other field::

   label: vaxa-smacks
   channel: FITC-A
   gating: 60%
   wells:
      0mM: [A1,A2,A3]
      1mM: [B1,B2,B3]
      5mM: [C1,C2,C3]
   
Once you have a YAML metadata file, you can use ``fcmcmp`` to read it::

   >>> import fcmcmp, pprint
   >>> experiments = fcmcmp.load_experiments('my_plate.yml')
   >>> pprint.pprint(experiments)
   [{'label': 'vaxadrin',
     'wells': {'with': [Well(B1), Well(B2), Well(B3)],
               'without': [Well(A1), Well(A2), Well(A3)]}},
    {'label': 'vaxamaxx',
     'wells': {'with': [Well(C1), Well(C2), Well(C3)],
               'without': [Well(A1), Well(A2), Well(A3)]}}]

The data structure returned is little more than a list of dictionaries, which 
should be easy to work with in pretty much any context.  The wells are 
represented by ``Well`` objects, which have only three attributes:

- ``Well.label``: The name used to reference the well in the YAML file.  
- ``Well.data``: A ``pandas.DataFrame`` containing all the data associated 
  with the well, parsed using the excellent ``fcsparse`` library.
- ``Well.meta``: A dictionary containing any metadata associated with the 
  well, also parsed using ``fcsparse``.

Note that if you reference the same well more than once (e.g. for controls that 
apply to all of your experiments), each reference is parsed separately and gets 
its own copy of all the data.

Working with the data
~~~~~~~~~~~~~~~~~~~~~
Once the experiments are loaded into python as described above, ``fcmcmp`` 
provides a couple ways to interact with them.  The first is to apply one or 
more of a handful of pre-defined "processing steps"::

   >>> ch = 'FITC-A', 'PE-Texas Red-A'
   >>> p1 = fcmcmp.GateEarlyEvents(throwaways_secs=2)
   >>> p1(experiments)
   >>> p2 = fcmcmp.GateSmallCells(threshold=40, save_size_col=True)
   >>> p2(experiments)
   >>> p3 = fcmcmp.GateNonPositiveEvents(ch)
   >>> p3(experiments)
   >>> p4 = fcmcmp.LogTransformation(ch)
   >>> p4(experiments)
   >>> p5 = fcmcmp.KeepRelevantChannels(ch)
   >>> p5(experiments)

In this example:

- ``GateEarlyEvents`` discards the first few seconds of data, which is useful 
  when you're using a high-throughput sampler and you suspect that cells from 
  the previous well are being recorded at the beginning of each well.
- ``GateSmallCells`` combines the ``FSC-A`` and ``SSC-A`` channels to estimate 
  how the size of each event, then discards any events below the given 
  percentile (40% in this example).
- ``GateNonPositiveEvents`` discards negative data on the specified channels.  
  I have to admit that I don't understand how "fluorescence peak area" data can 
  be negative, but in any case this can be important if you want to work with 
  the logarithm of your data, because of course you can't take the logarithm of 
  negative data.
- ``LogTransform`` takes the logarithm of the data in the specified channels.  
  This is a very standard processing step for fluorescent channels.
- ``KeepRelevantChannels`` discards all the data for any channels that aren't 
  explicitly listed.  This is mostly useful for when you're printing out data 
  to the terminal and don't want to be distracted by channels you collected but 
  aren't interested in at the moment.

Instead of calling each processing step individually, you can also use the 
``run_all_processing_steps()`` function to call them all at once.  If you do 
this, you don't even need to make a variable for each step::

   >>> fcmcmp.GateEarlyEvents(throwaways_secs=2)
   >>> fcmcmp.GateSmallCells(threshold=40, save_size_col=True)
   >>> fcmcmp.GateNonPositiveEvents(ch)
   >>> fcmcmp.LogTransformation(ch)
   >>> fcmcmp.KeepRelevantChannels(ch)
   >>> fcmcmp.run_all_processing_steps()

You can also write your own processing steps by inheriting from either 
``ProcessingStep`` or ``GatingStep`` and reimplementing the proper methods.  
``ProcessingStep`` is for general transformations and has two virtual methods: 
``process_experiment()`` and ``process_well()``.  The former is called once for 
each experiment and should transform that experiment in place.  The latter is 
called once for each well and can either modify the well in place (and return 
None) or return the processed data, which will overwrite the original data.

``GatingStep`` is specifically for transformations regarding which data points 
to keep and which to throw out.  It is itself a ``ProcessingStep``, but it has 
a different virtual method(): ``gate()``.  This method is called on each well 
and should return a boolean numpy array.  Those indices that are ``False`` will 
be thrown out, those that are ``True`` will be kept.

The second way to interact with the experiments is to use the ``yield_wells()`` 
and ``yield_unique_wells()`` functions.  These are both `generators`__ which 
iterate through all of your experiments and yield each well one at a time.  The 
purpose of these functions is to make the nested ``experiments`` data structure 
seem more like a flat list::

   >>> for experiment, condition, well in fcmcmp.yield_wells(experiments):
   >>>     print(experiment, condition, well)

Both functions take an optional keyword argument.  If given, only wells with a 
matching experiment label, condition, or well label will be returned.  The only 
difference between ``yield_wells()`` and ``yield_unique_wells()`` is that the 
former won't yield the same well twice.  This is important because the same 
well can certainly be included in many different experiments.

__ https://jeffknupp.com/blog/2013/04/07/improve-your-python-yield-and-generators-explained/

Bugs and new features
=====================
Use the GitHub issue tracker if you find any bugs or would like to see any new 
features.  I'm also very open to pull requests.
