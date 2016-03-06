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
raw FCS data into a pandas data frame.

.. image:: https://travis-ci.org/kalekundert/fcmcmp.svg?branch=master
    :target: https://travis-ci.org/kalekundert/fcmcmp

.. image:: https://coveralls.io/repos/github/kalekundert/fcmcmp/badge.svg?branch=master 
   :target: https://coveralls.io/github/kalekundert/fcmcmp?branch=master 

Installation
============
``fcmcmp`` is available on PyPI::

   pip install fcmcmp

Only python>=3.2 is supported.

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
by adding the following header before the "label"/"wells" sections::

   plate: path/to/my_plate
   ---

You can even reference well from multiple plates in one file::

   plates:
      foo: path/to/foo_plate
      bar: path/to/bar_plate
   ---
   label: vaxascab
   wells:
      without: [foo/A1, foo/A2, foo/A3]
      with: [bar/A1, bar/A2, bar/A3]

Note that the "label" and "wells" fields are required, but you can add, remove, 
or rename any other field::

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
   >>> pprint.pprint(experiment)
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

Bugs and new features
=====================
Use the GitHub issue tracker if you find any bugs or would like to see any new 
features.  I'm also very open to pull requests.
