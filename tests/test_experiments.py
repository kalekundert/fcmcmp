#!/usr/bin/env python3

"""
Description of the experiment data structure.
"""

import pytest, fcmcmp, pandas as pd
from pathlib import Path

dummy_data = Path(__file__).parent / 'dummy_data'

def test_empty_file():
    with pytest.raises(fcmcmp.UsageError) as exc_info:
        fcmcmp.load_experiments(dummy_data / 'empty_file.yml')
    assert "is empty" in str(exc_info.value)

def test_missing_label():
    with pytest.raises(fcmcmp.UsageError) as exc_info:
        fcmcmp.load_experiments(dummy_data / 'missing_label.yml')
    assert "missing a label" in str(exc_info.value)

def test_missing_wells():
    with pytest.raises(fcmcmp.UsageError) as exc_info:
        fcmcmp.load_experiments(dummy_data / 'missing_wells.yml')
    assert "doesn't have any wells" in str(exc_info.value)

def test_unparseable_well():
    with pytest.raises(fcmcmp.UsageError) as exc_info:
        fcmcmp.load_experiments(dummy_data / 'unparseable_well.yml')
    assert "Can't parse well name" in str(exc_info.value)

def test_nonexistent_well():
    with pytest.raises(fcmcmp.UsageError) as exc_info:
        fcmcmp.load_experiments(dummy_data / 'nonexistent_well.yml')
    assert "No *.fcs files found for well" in str(exc_info.value)

def test_unspecified_plate():
    with pytest.raises(fcmcmp.UsageError) as exc_info:
        fcmcmp.load_experiments(dummy_data / 'unspecified_plate.yml')
    assert "No plates specified" in str(exc_info.value)

def test_undefined_plate():
    with pytest.raises(fcmcmp.UsageError) as exc_info:
        fcmcmp.load_experiments(dummy_data / 'undefined_plate.yml')
    assert "Plate 'foo' not defined." in str(exc_info.value)

def test_ambiguous_header():
    with pytest.raises(fcmcmp.UsageError) as exc_info:
        fcmcmp.load_experiments(dummy_data / 'ambiguous_header.yml')
    assert "Too many fields in 'plates' header." in str(exc_info.value)

def test_parse_well():
    from fcmcmp import parse_well

    bad_names = [
            'A',        # No well number.
            'AB1',      # Two well letters.
            'a1',       # Lowercase well letter.
            '!',        # Random punctuation.
            '1',        # No well letter.
            '/A1',      # Empty plate name
            'foo/',     # No well name.
    ]
    for name in bad_names:
        with pytest.raises(fcmcmp.UsageError):
            fcmcmp.parse_well(name)

    good_names = {
            'A1': (None, 'A1'),
            'A01': (None, 'A01'),
            'foo/A1': ('foo', 'A1'),
            'hello world!/A1': ('hello world!', 'A1'),
    }
    for name, expected_result in good_names.items():
        assert fcmcmp.parse_well(name) == expected_result

def test_infer_plate_1():
    experiments = fcmcmp.load_experiments(dummy_data / 'plate_1.yml')

    assert experiments[0]['label'] == 'sgGFP'
    assert experiments[0]['channel'] == 'FITC-A'

    for experiment in experiments:
        for wells in experiment['wells'].values():
            for well in wells:
                assert isinstance(well, pd.DataFrame)

def test_specify_plate_1():
    experiments = fcmcmp.load_experiments(dummy_data / 'specify_plate_1.yml')

    assert experiments[0]['label'] == 'sgRFP'
    assert experiments[0]['channel'] == 'PE-Texas Red-A'

    for experiment in experiments:
        for wells in experiment['wells'].values():
            for well in wells:
                assert isinstance(well, pd.DataFrame)

def test_specify_both_plates():
    experiments = fcmcmp.load_experiments(dummy_data / 'specify_both_plates.yml')

    assert experiments[0]['label'] == 'sgNull'
    assert experiments[0]['channel'] == 'FSC-A'

    for experiment in experiments:
        for wells in experiment['wells'].values():
            for well in wells:
                assert isinstance(well, pd.DataFrame)

def test_multiple_experiments():
    experiments = fcmcmp.load_experiments(dummy_data / 'multiple_experiments.yml')

    assert experiments[0]['label'] == 'sgGFP'
    assert experiments[0]['channel'] == 'FITC-A'
    assert experiments[1]['label'] == 'sgRFP'
    assert experiments[1]['channel'] == 'PE-Texas Red-A'

    for experiment in experiments:
        for wells in experiment['wells'].values():
            for well in wells:
                assert isinstance(well, pd.DataFrame)

