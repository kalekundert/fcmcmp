#!/usr/bin/env python3

import sys, re, yaml, logging, fcsparser, subprocess
from pathlib import Path
from natsort import natsorted
from pprint import pprint

def parse_well_label(label):
    fields = label.rsplit('/', 1)
    if len(fields) == 1:
        return None, fields[0]
    else:
        return fields

def load_experiments(config_path, well_glob='**/*_{}_*.fcs'):
    config_path = Path(config_path)

    if config_path.suffix == '.py':
        py_command = 'python', str(config_path)
        yml_config = subprocess.check_output(py_command)
        documents = list(yaml.load_all(yml_config))

    else:
        with config_path.open() as file:
            documents = list(yaml.load_all(file))

    if not documents:
        raise UsageError("'{}' is empty.".format(config_path))

    # Find the *.fcs data files relevant to this experiment.  If there is a 
    # document with a mapping called "plates:", treat the values as paths to 
    # data directories and the keys as names that can refer to the directories 
    # in the rest of the file.  If there is a document with an assignment 
    # called "plate:", treat it as the path to the only data directory that 
    # will be used in the rest of the file.  If no data directory is specified 
    # by either of these two mechanisms, try to infer a path from the name of 
    # the YAML file itself.

    inferred_path = config_path.parent / config_path.stem

    def str_to_path(s):
        return Path(s) if Path(s).is_absolute() else config_path.parent/s

    def clean_up_plate_document():
        if len(documents[0]) > 1:
            raise UsageError("Too many fields in 'plates' header.")
        del documents[0]


    if 'plates' in documents[0]:
        plates = {k: str_to_path(v) for k,v in documents[0]['plates'].items()}
        clean_up_plate_document()
    elif 'plate' in documents[0]:
        plates = {None: str_to_path(documents[0]['plate'])}
        clean_up_plate_document()
    elif inferred_path.is_dir():
        plates = {None: inferred_path}
    else:
        plates = {}

    # Construct and fill in a list of experiments.  Well names are converted 
    # into paths based on the user-given glob pattern, then parsed and stored 
    # as pandas data frames.  Note that if a well is referenced more than once, 
    # it will also be parsed more than once.  This guarantees that each well 
    # can be processed independently, which is important for many workflows.

    experiments = []
    includes = {}

    def load_well(label):
        # Short-circuit the case where the well has already been loaded, which 
        # is triggered by the "from" external reference machinery.

        if isinstance(label, Well):
            return label

        # Parse well and plate names from the given label.  The plate name is 
        # optional, because often there is only one.

        plate, well = parse_well_label(label)

        # Find the *.fcs file referenced by the given label.

        if plate not in plates:
            raise UsageError(
                    "Plate '{}' not defined.".format(plate)
                    if plate is not None else
                    "No default plate defined.")

        plate_path = plates[plate]
        well_paths = list(plate_path.glob(well_glob.format(well)))
        if len(well_paths) == 0:
            raise UsageError("No *.fcs files found for well '{}'".format(label))
        if len(well_paths) > 1:
            raise UsageError("Multiple *.fcs files found for well '{}'".format(label))
        well_path = well_paths[0]

        # Load the cell data for the given well.
        
        logging.info('Loading {}'.format(well_path.name))
        meta, data = fcsparser.parse(str(well_path))
        return Well(label, meta, data)


    for experiment in documents:
        if not experiment:
            raise UsageError("An empty experiment was found.\nDid you accidentally leave '---' at the end of the file?")

        # Reference experiments from other files if the special "from" keyword 
        # is present.

        if 'from' in experiment:
            experiment = load_experiment(
                    config_path.parent / experiment['from'],
                    experiment['label'])

        # Make sure each document has a label and a list of wells.  Other key- 
        # value pairs can be present but are not required.

        if 'label' not in experiment:
            raise UsageError("The following experiment is missing a label:\n\n{}".format(yaml.dump(experiment)))
        if 'wells' not in experiment:
            raise UsageError("The following experiment doesn't have any wells:\n\n{}".format(yaml.dump(experiment)))

        # Set the well data for the comparison.  This requires converting the 
        # well names we were given into paths and parsing those files.

        for well_type, well_names in experiment['wells'].items():
            experiment['wells'][well_type] = [load_well(x) for x in well_names]

        experiments.append(experiment)

    return experiments
        
def load_experiment(config_path, experiment_label, well_glob='**/*_{}_*.fcs'):
    experiments = load_experiments(config_path, well_glob=well_glob)
    for experiment in experiments:
        if experiment['label'] == experiment_label:
            return experiment
    raise UsageError("No experiment named '{}'".format(experiment_label))
        

class Well:

    def __init__(self, label, meta, data):
        self.label = label
        self.meta = meta
        self.data = data

    def __repr__(self):
        return 'Well({})'.format(self.label)



def define_96_well_plates(define_well, define_experiment=lambda expt: None,
        plate=None, plates=None, plate_order=None, layout='col/row/plate',
        **extra_params):

    header = []
    script_name = Path(sys.argv[0]).stem

    # If the user didn't specify any plates:
    if plate is None and plates is None:
        plates = {None: ''}

    # If the user specified a single plate:
    elif plate is not None and plates is None:
        header.append({'plate': plate.replace('$', script_name)})
        plates = {None: plate}

    # If the user specifies multiple plates:
    elif plate is None and plates is not None:
        header.append({'plates': {
            k: v.replace('$', script_name) for k, v in plates.items()}})

    else:
        raise UsageError("cannot specify both 'plate' and 'plates'")

    # Set the order in which the plates should be considered.  The default 
    # order is alphabetical.

    if plate_order is None:
        plate_order = natsorted(plates)

    # Understand how the plates are indexed, i.e. do the indices increment by 
    # column then row then plate, or by column then plate then row, etc.

    steps = layout.split('/')

    if len(steps) == 2:
        steps.append('plate')
    if set(steps) != {'row', 'col', 'plate'}:
        raise UsageError("invalid layout: '{}'".format(layout))

    strides = {
            'col': 12,
            'row': 8,
            'plate': len(plates),
    }
    divisors = {
            steps[0]: 1,
            steps[1]: strides[steps[0]],
            steps[2]: strides[steps[0]] * strides[steps[1]],
    }

    # Create experiments by iterating through each well and associating a 
    # labels and a condition with each one.

    experiments = []

    for i in range(96 * len(plates)):

        # Figure out which row, column, and plate this index refers to.

        row = (i // divisors['row']) % strides['row']
        col = (i // divisors['col']) % strides['col']
        plate = plate_order[(i // divisors['plate']) % strides['plate']]

        # Get the experiment and condition to associate with this well from the 
        # user.  Skip this well if define_well() returns None.

        well = WellCursor96(i, row, col, plate)
        definition = define_well(well)

        if definition is None:
            continue

        label, condition = definition

        # If an experiment with this label already exists, find it.  
        # Otherwise create an empty experiment data structure and add 
        # it to the list of experiments.

        try:
            experiment = next(
                    expt for expt in experiments
                    if expt['label'] == label)

        except StopIteration:
            experiment = extra_params.copy()
            experiment['label'] = label
            experiment['wells'] = {}
            experiments.append(experiment)

        # Associate this well with the given condition.

        experiment['wells'].setdefault(condition, []).append(str(well))

    # Allow the user to add custom parameters to each experiment.

    for experiment in experiments:
        define_experiment(experiment)

    # Export the experiments to YAML and either print them to stdout or save 
    # them to a file, depending on the command-line arguments.

    output_path = script_name + '.yml'

    import docopt
    args = docopt.docopt("""\
Usage:
    {script_name}.py [-ocq]

Options:
    -o --output
        Save the experimental layout to ``{output_path}``

    -c --count
        Print the number of experiments contained these plates.

    -q --quiet
        Don't print anything.  This is useful if you want to print some 
        debugging information in your callbacks and don't wat to get flooded 
        with YAML text.
""".format(**locals()))

    # I wanted to use yaml.dump_all() here, but yaml.dump() has a better 
    # default indentation algorithm.

    dump_config = lambda **kwargs: '---\n'.join(
            yaml.dump(x, **kwargs) for x in header + experiments)

    if args['--output']:
        
        with open(output_path, 'w') as file:
            file.write(dump_config())
    elif args['--count']:
        print(len(experiments))
    elif args['--quiet']:
        pass
    else:
        print(dump_config())

class WellCursor96:

    def __init__(self, index, row, col, plate):
        self._index = index
        self._row = row
        self._col = col
        self._plate = plate

    def __repr__(self):
        return self.label

    def __eq__(self, other):
        try:
            return (self.index, self.row, self.col, self.plate) == \
                   (other.index, other.row, other.col, other.plate)

        except AttributeError:
            other_plate, other_well = parse_well_label(str(other))
            other_well_match = re.match('([A-H])([0-9]{1,2})', other_well)

            if not other_well_match:
                raise UsageError("can't compare {} to {}".format(other, self))

            other_row = list('ABCDEFGH').index(other_well_match.group(1))
            other_col = int(other_well_match.group(2)) - 1

            return (self.row, self.col, self.plate) == \
                   (other_row, other_col, other_plate)

    @property
    def index(self):
        return self._index

    @property
    def row(self):
        return self._row

    @property
    def row_abc(self):
        return 'ABCDEFGH'[self.row]

    @property
    def col(self):
        return self._col

    @property
    def plate(self):
        return self._plate

    @property
    def label(self):
        label = '{}{:02d}'.format(self.row_abc, self.col + 1)

        if self.plate:
            label = '{}/{}'.format(self.plate, label)

        return label



class UsageError (Exception):
    """
    Indicate errors caused by invalid user input.
    """
    def __init__(self, message):
        super().__init__(message)
    
        

