#!/usr/bin/env python3

import pytest, fcmcmp, pandas as pd
from pathlib import Path

dummy_data = Path(__file__).parent / 'dummy_data'

def check_wells(experiments, **expected_wells):
    for expriment, condition, well in fcmcmp.yield_wells(experiments):
        assert condition in expected_wells
        assert well.label in expected_wells[condition]
        assert isinstance(well.meta, dict)
        assert isinstance(well.data, pd.DataFrame)


def test_well_repr():
    well = fcmcmp.Well('A1', None, None)
    assert repr(well) == 'Well(A1)'

def test_empty_file():
    with pytest.raises(fcmcmp.UsageError) as exc_info:
        fcmcmp.load_experiments(dummy_data / 'empty_file.yml')
    assert "is empty" in str(exc_info.value)

def test_empty_experiment():
    with pytest.raises(fcmcmp.UsageError) as exc_info:
        fcmcmp.load_experiments(dummy_data / 'empty_experiment.yml')
    assert "empty experiment was found" in str(exc_info.value)

def test_missing_label():
    with pytest.raises(fcmcmp.UsageError) as exc_info:
        fcmcmp.load_experiments(dummy_data / 'missing_label.yml')
    assert "missing a label" in str(exc_info.value)

def test_missing_wells():
    with pytest.raises(fcmcmp.UsageError) as exc_info:
        fcmcmp.load_experiments(dummy_data / 'missing_wells.yml')
    assert "doesn't have any wells" in str(exc_info.value)

def test_nonexistent_well():
    with pytest.raises(fcmcmp.UsageError) as exc_info:
        fcmcmp.load_experiments(dummy_data / 'nonexistent_well.yml')
    assert "No *.fcs files found for well" in str(exc_info.value)

def test_ambiguous_well():
    with pytest.raises(fcmcmp.UsageError) as exc_info:
        fcmcmp.load_experiments(dummy_data / 'ambiguous_well.yml')
    assert "Multiple *.fcs files found for well" in str(exc_info.value)

def test_unspecified_plate():
    with pytest.raises(fcmcmp.UsageError) as exc_info:
        fcmcmp.load_experiments(dummy_data / 'unspecified_plate.yml')
    assert "No default plate defined" in str(exc_info.value)

def test_undefined_plate():
    with pytest.raises(fcmcmp.UsageError) as exc_info:
        fcmcmp.load_experiments(dummy_data / 'undefined_plate.yml')
    assert "Plate 'foo' not defined." in str(exc_info.value)

def test_ambiguous_header():
    with pytest.raises(fcmcmp.UsageError) as exc_info:
        fcmcmp.load_experiments(dummy_data / 'ambiguous_header.yml')
    assert "Too many fields in 'plates' header." in str(exc_info.value)

def test_infer_plate_1():
    experiments = fcmcmp.load_experiments(dummy_data / 'plate_1.yml')

    assert experiments[0]['label'] == 'sgGFP'
    assert experiments[0]['channel'] == 'FITC-A'

    check_wells(experiments, before=['A1'], after=['B1'])

def test_specify_plate_1():
    experiments = fcmcmp.load_experiments(dummy_data / 'specify_plate_1.yml')

    assert experiments[0]['label'] == 'sgRFP'
    assert experiments[0]['channel'] == 'PE-Texas Red-A'

    check_wells(experiments, before=['A1'], after=['B1'])

def test_specify_both_plates():
    experiments = fcmcmp.load_experiments(dummy_data / 'specify_both_plates.yml')

    assert experiments[0]['label'] == 'sgNull'
    assert experiments[0]['channel'] == 'FSC-A'

    check_wells(experiments,
            before=['p1/A1', 'p2/A1'], after=['p1/B1', 'p2/B1'])

def test_multiple_experiments():
    experiments = fcmcmp.load_experiments(dummy_data / 'multiple_experiments.yml')

    assert experiments[0]['label'] == 'sgGFP'
    assert experiments[0]['channel'] == 'FITC-A'
    assert experiments[1]['label'] == 'sgRFP'
    assert experiments[1]['channel'] == 'PE-Texas Red-A'

    check_wells(experiments, before=['A1'], after=['B1'])

def test_external_reference():
    experiments = fcmcmp.load_experiments(dummy_data / 'external_reference.yml')

    assert experiments[0]['label'] == 'sgGFP'
    assert experiments[0]['channel'] == 'FITC-A'

    check_wells(experiments, before=['A1'], after=['B1'])

def test_python_config():
    experiments = fcmcmp.load_experiments(dummy_data / 'plate_1.py')

    assert experiments[0]['label'] == 'sgGFP'
    assert experiments[0]['channel'] == 'FITC-A'

    check_wells(experiments, before=['A1'], after=['B1'])

def test_load_experiment():
    gfp_experiment = fcmcmp.load_experiment(
            dummy_data / 'multiple_experiments.yml', 'sgGFP')
    rfp_experiment = fcmcmp.load_experiment(
            dummy_data / 'multiple_experiments.yml', 'sgRFP')

    assert gfp_experiment['label'] == 'sgGFP'
    assert gfp_experiment['channel'] == 'FITC-A'
    assert rfp_experiment['label'] == 'sgRFP'
    assert rfp_experiment['channel'] == 'PE-Texas Red-A'

    with pytest.raises(fcmcmp.UsageError) as exc_info:
        fcmcmp.load_experiment(
                dummy_data / 'multiple_experiments.yml', 'foobar')
    assert "No experiment named 'foobar'" in str(exc_info.value)


