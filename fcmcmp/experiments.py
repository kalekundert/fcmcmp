#!/usr/bin/env python3

from pprint import pprint
import pandas; pandas.set_option('display.large_repr', 'info')

def load_experiments(yml_path, well_glob='**/*_{}_*.fcs'):
    import yaml, logging, fcsparser
    from pathlib import Path

    yml_path = Path(yml_path)
    with yml_path.open() as file:
        documents = [x for x in yaml.load_all(file)]

    if not documents:
        raise UsageError("'{}' is empty.".format(yml_path))

    # Find the *.fcs data files relevant to this experiment.  If there is a 
    # document with a mapping called "plates:", treat the values as paths to 
    # data directories and the keys as names that can refer to the directories 
    # in the rest of the file.  If there is a document with an assignment 
    # called "plate:", treat it as the path to the only data directory that 
    # will be used in the rest of the file.  If no data directory is specified 
    # by either of these two mechanisms, try to infer a path from the name of 
    # the YAML file itself.

    inferred_path = yml_path.parent / yml_path.stem

    def str_to_path(s):
        return Path(s) if Path(s).is_absolute() else yml_path.parent/s

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
        raise UsageError("No plates specified.")

    # Construct and fill in a list of experiments.  Well names are converted 
    # into paths based on the user-given glob pattern, then parsed and stored 
    # as pandas data frames.  Note that if a well is referenced more than once, 
    # it will also be parsed more than once.  This guarantees that each well 
    # can be processed independently, which is important for many workflows.

    experiments = []

    def load_well(name):

        # Parse well and plate names from the given name.  The plate name is 
        # optional, because often there is only one.

        fields = name.rsplit('/', 1)
        if len(fields) == 1:
            plate, well = None, fields[0]
        else:
            plate, well = fields

        # Find the *.fcs file referenced by the given name.

        if plate not in plates:
            raise UsageError(
                    "Plate '{}' not defined.".format(plate)
                    if plate is not None else
                    "No default plate defined.")

        plate_path = plates[plate]
        well_paths = list(plate_path.glob(well_glob.format(well)))
        if len(well_paths) == 0:
            raise UsageError("No *.fcs files found for well '{}'".format(name))
        if len(well_paths) > 1:
            raise UsageError("Multiple *.fcs files found for well '{}'".format(name))
        well_path = well_paths[0]

        # Load the cell data for the given well.
        
        logging.info('Loading {}'.format(well_path.name))
        meta, data = fcsparser.parse(str(well_path))
        return Well(name, meta, data)


    for experiment in documents:
        experiments.append(experiment)

        # Make sure each document has a label and a list of wells.  Other key- 
        # value pairs can be present but are not required.

        if not experiment:
            raise UsageError("An empty experiment was found.\nDid you accidentally leave '---' at the end of the file?")
        if 'label' not in experiment:
            raise UsageError("The following experiment is missing a label:\n\n{}".format(yaml.dump(experiment)))
        if 'wells' not in experiment:
            raise UsageError("The following experiment doesn't have any wells:\n\n{}".format(yaml.dump(experiment)))

        # Set the well data for the comparison.  This requires converting the 
        # well names we were given into paths and parsing those files.

        for well_type, well_names in experiment['wells'].items():
            experiment['wells'][well_type] = [load_well(x) for x in well_names]

    return experiments
        
def load_experiment(yml_path, experiment_name, well_glob='**/*_{}_*.fcs'):
    experiments = load_experiments(yml_path, well_glob=well_glob)
    for experiment in experiments:
        if experiment['label'] == experiment_name:
            return experiment
    raise UsageError("No experiment named '{}'".format(experiment_name))
        
def yield_wells(experiments):
    for experiment in experiments:
        for condition in experiment['wells']:
            for well in experiment['wells'][condition]:
                yield experiment, condition, well


class Well:

    def __init__(self, label, meta, data):
        self.label = label
        self.meta = meta
        self.data = data

    def __repr__(self):
        return 'Well({})'.format(self.label)


class UsageError (Exception):
    """
    Indicate errors caused by invalid user input.
    """
    def __init__(self, message):
        super().__init__(message)
    
        

