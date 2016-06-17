#!/usr/bin/env python3

import pytest, fcmcmp, pandas as pd
from nonstdlib import approx

def dummy_data(data):
    df = pd.DataFrame.from_dict(data)
    well = fcmcmp.Well('A1', {}, df)
    experiment = {
            'label': 'dummy',
            'wells': {
                'dummy': [well],
            }
    }
    return [experiment], well

def test_yield_wells():
    experiments, well = dummy_data({
        'FITC-A': [100],
    })

    experiment_i, condition_i, well_i = next(fcmcmp.yield_wells(experiments))

    assert experiment_i == experiments[0]
    assert condition_i == 'dummy'
    assert well_i.label == 'A1'

def test_keep_relevant_channels():
    experiments, well = dummy_data({
        'FSC-A': [100],
        'FSC-W': [100],
        'FSC-H': [100],
    })

    keep_relevant_channels = fcmcmp.KeepRelevantChannels()
    keep_relevant_channels.channels = ['FSC-A']
    keep_relevant_channels(experiments)

    assert well.data.columns == ['FSC-A']

def test_log_transformation():
    experiments, well = dummy_data({
        'FSC-A': [100, 200, 300, 400, 500, 600],
        'FITC-A': [1, 10, 100, 1000, 10000, 100000],
    })

    log_transformation = fcmcmp.LogTransformation()
    log_transformation.channels = ['FITC-A']
    log_transformation(experiments)

    assert well.data['FSC-A'].tolist() == approx([100, 200, 300, 400, 500, 600])
    assert well.data['FITC-A'].tolist() == approx([0, 1, 2, 3, 4, 5])

def test_gate_nonpositive_events():
    experiments, well = dummy_data({
        'FSC-A':  [-1,-1,-1, 0, 0, 0, 1, 1, 1],
        'FITC-A': [-1, 0, 1,-1, 0, 1,-1, 0, 1],
    })

    gate_nonpositive = fcmcmp.GateNonPositiveEvents()
    gate_nonpositive.channels = ['FITC-A']
    gate_nonpositive(experiments)

    assert well.data['FSC-A'].tolist() == [-1, 0, 1]
    assert well.data['FITC-A'].tolist() == [1, 1, 1]

def test_gate_small_cells():
    experiments, well = dummy_data({
        'FSC-A': [1, 2, 3, 4, 5],
        'SSC-A': [1, 2, 3, 4, 5],
    })

    gate_small_cells = fcmcmp.GateSmallCells()
    gate_small_cells.save_size_col = True
    gate_small_cells.threshold = 0
    gate_small_cells(experiments)

    assert well.data['FSC-A'].tolist() == [1, 2, 3, 4, 5]
    assert well.data['SSC-A'].tolist() == [1, 2, 3, 4, 5]
    assert well.data['FSC-A + m * SSC-A'].tolist() == [2, 4, 6, 8, 10]

    gate_small_cells.threshold = 50
    gate_small_cells(experiments)

    assert well.data['FSC-A'].tolist() == [3, 4, 5]
    assert well.data['SSC-A'].tolist() == [3, 4, 5]
    assert well.data['FSC-A + m * SSC-A'].tolist() == [6, 8, 10]

def test_gate_early_events():
    experiments, well = dummy_data({
        'Time':  [0, 1, 2, 3, 4, 5],
    })
    well.meta['$TIMESTEP'] = '2'

    gate_early_events = fcmcmp.GateEarlyEvents()
    gate_early_events.throwaway_secs = 0
    gate_early_events(experiments)

    assert well.data['Time'].tolist() == [0, 1, 2, 3, 4, 5]

    gate_early_events.throwaway_secs = 4
    gate_early_events(experiments)

    assert well.data['Time'].tolist() == [2, 3, 4, 5]

def test_all_processing_steps():
    experiments, well = dummy_data({
        'Time':   [ 0, 1, 2, 3, 4, 5],
        'FITC-A': [ 1, 1, 1, 1,-1,-1],
    })
    well.meta['$TIMESTEP'] = '2'

    fcmcmp.clear_all_processing_steps()

    gate_nonpositive = fcmcmp.GateNonPositiveEvents()
    gate_nonpositive.channels = ['FITC-A']
    gate_early_events = fcmcmp.GateEarlyEvents()
    gate_early_events.throwaway_secs = 4

    fcmcmp.run_all_processing_steps(experiments)

    assert well.data['Time'].tolist() == [2, 3]
    assert well.data['FITC-A'].tolist() == [1, 1]


