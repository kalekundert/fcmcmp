#!/usr/bin/env python3

import numpy as np
from pprint import pprint

def run_all_processing_steps(experiments):
    for step in _all_processing_steps:
        step(experiments)

_all_processing_steps = []


class ProcessingStep:
    """
    A modular transformation that can be applied to flow cytometry data.

    The purpose of this class is primarily to abstract the process of iterating 
    through the data structure created by load_experiments().  Each experiment 
    can contain a number of flow cytometry data frames.  Iterating through all 
    of them to apply a common transformation is common enough that it was worth 
    supporting with a bit of a framework, and that's what this class is.
    """

    def __new__(cls):
        """
        Keep track of all the processing steps that get instantiated.  This 
        functionality is required by run_all_processing_steps().
        """
        # Implement __new__() instead of __init__() because it's less likely 
        # that subclasses will overwrite __new__() and forget to call this 
        # method.
        step = super().__new__(cls)
        _all_processing_steps.append(step)
        return step

    def __call__(self, experiments):
        """
        Apply this processing step to all of the given experiments.
        
        The actual processing is delegated to process_experiment(), which can 
        be overwritten by subclasses.  The default process_experiment() calls 
        process_well() on each well, which nicely abstracts the process of 
        iterating through the experiment data structure.
        """
        for experiment in experiments:
            self.process_experiment(experiment)

    def process_experiment(self, experiment):
        """
        Iterate over all the wells in the given experiment.
        
        The processing of each well is delegated to process_well(), which is an 
        abstract method.  If process_well() returns a data frame, it replaces 
        the existing well data.  If process_well() returns None, it is assumed 
        that the well data was modified in place.
        """
        for condition, wells in experiment['wells'].items():
            for i, well in enumerate(wells):
                processed_well = self.process_well(experiment, well)
                if processed_well is not None:
                    experiment['wells'][condition][i] = processed_well

    def process_well(self, experiment, well):   # (abstract)
        """
        Process the data from an individual well in any way.

        This method can either return a new data frame, which will replace the 
        existing one for the given well, or it can just modify the given well 
        in place.
        """
        raise NotImplementedError


class KeepRelevantChannels(ProcessingStep):
    """
    Discard any channels that aren't explicitly listed.

    This is just useful for making processing a little faster and output a 
    little cleaner if you collected data for more channels than you needed to, 
    for whatever reason.
    """

    def __init__(self, channels=None):
        self.channels = None

    def process_well(self, experiment, well):
        return well.reindex(columns=self.channels)


class LogTransformation(ProcessingStep):

    def __init__(self, channels=None):
        self.channels = channels or []

    def process_well(self, experiment, well):
        for channel in self.channels:
            well[channel] = np.log10(well[channel])


class GatingStep(ProcessingStep):

    def process_well(self, experiment, well):
        return well.drop(well.index[self.gate(experiment, well)])

    def gate(self, experiment, well):
        raise NotImplementedError


class GateNonPositiveEvents(GatingStep):

    def __init__(self, channels=None):
        self.channels = None

    def gate(self, experiment, well):
        channels = self.channels or well.columns
        masks = [well[channel] <= 0 for channel in channels]
        return np.any(np.vstack(masks), axis=0)


