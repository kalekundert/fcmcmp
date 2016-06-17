#!/usr/bin/env python3

import numpy as np
from pprint import pprint

def yield_wells(experiments, keyword=None):
    for experiment in experiments:
        for condition in experiment['wells']:
            for well in experiment['wells'][condition]:
                if keyword is None or \
                        keyword in experiment['label'] or \
                        keyword == condition or \
                        keyword == well.label:
                    yield experiment, condition, well

def yield_unique_wells(experiments, keyword=None):
    previous_wells = set()
    for experiment, condition, well in yield_wells(experiments, keyword):
        if well not in previous_wells:
            previous_wells.add(well)
            yield experiment, condition, well

def clear_all_processing_steps():
    global _all_processing_steps
    _all_processing_steps = []

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
                processed_data = self.process_well(experiment, well)
                if processed_data is not None:
                    experiment['wells'][condition][i].data = processed_data

    def process_well(self, experiment, well):   # (abstract)
        """
        Process the data from an individual well in any way.

        This method can either return a new data frame, which will replace the 
        existing one for the given well, or it can just modify the given well 
        in place.
        """
        raise NotImplementedError(self.__class__.__name__)


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
        return well.data.reindex(columns=self.channels)


class LogTransformation(ProcessingStep):

    def __init__(self, channels=None):
        self.channels = channels or []

    def process_well(self, experiment, well):
        for channel in self.channels:
            well.data[channel] = np.log10(well.data[channel])


class GatingStep(ProcessingStep):

    def process_well(self, experiment, well):
        selection = self.gate(experiment, well)
        if selection is not None:
            return well.data.drop(well.data.index[selection])

    def gate(self, experiment, well):
        raise NotImplementedError


class GateNonPositiveEvents(GatingStep):

    def __init__(self, channels=None):
        self.channels = None

    def gate(self, experiment, well):
        channels = self.channels or well.data.columns
        masks = [well.data[channel] <= 0 for channel in channels]
        return np.any(np.vstack(masks), axis=0)


class GateSmallCells(GatingStep):

    def __init__(self, threshold=40, save_size_col=False):
        self.threshold = threshold
        self.save_size_col = save_size_col

    def gate(self, experiment, well):
        from scipy.stats import linregress
        fsc, ssc = well.data['FSC-A'], well.data['SSC-A']
        m, b, *quality = linregress(fsc, ssc)
        sizes = fsc + m * ssc
        if self.save_size_col:
            well.data['FSC-A + m * SSC-A'] = sizes
        return sizes < np.percentile(sizes, self.threshold)


class GateEarlyEvents(GatingStep):

    def __init__(self, throwaway_secs=2):
        self.throwaway_secs = throwaway_secs

    def gate(self, experiment, well):
        secs = well.data['Time'] * float(well.meta['$TIMESTEP'])
        return secs < self.throwaway_secs
