"""
This module include multiple test cases to check the performance of the s2_tiles_supres script.
"""
import glob
import os
import json
from pathlib import Path
import tempfile

import rasterio
import pytest
import mock

from context import Superresolution, load_params, SyntheticImage


def test_get_max_min():
    """
    This method checks the get_min_max method.
    """
    dsr_xmin_exm, dsr_ymin_exm, dsr_xmax_exm, dsr_ymax_exm, dsr_area_exm = (0, 0, 5, 5, 36)

    test_dir = Path(tempfile.mkdtemp())
    valid_desc = ['B4, central wavelength 665 nm', 'B3, central wavelength 560 nm',
                  'B2, central wavelength 490 nm', 'B8, central wavelength 842 nm']
    test_img, _ = SyntheticImage(40, 40, 4, 'uint16', test_dir, 32640)\
        .create(pix_width=10, pix_height=10, valid_desc=valid_desc, seed=45)
    dsr = rasterio.open(test_img)
    dsr_xmin, dsr_ymin, dsr_xmax, dsr_ymax, dsr_area =\
        Superresolution.get_max_min(0, 0, 10, 10, dsr)

    assert dsr_xmin == dsr_xmin_exm
    assert dsr_ymin == dsr_ymin_exm
    assert dsr_xmax == dsr_xmax_exm
    assert dsr_ymax == dsr_ymax_exm
    assert dsr_area == dsr_area_exm


def test_to_xy():
    """
    This method checks to_xy method.
    """
    params = {'roi_x_y': [5, 5, 15, 15]}
    s_2 = Superresolution(params)
    dsr_x_exm = -575834
    dsr_y_exm = 66564
    test_dir = Path(tempfile.mkdtemp())
    valid_desc = ['B4, central wavelength 665 nm', 'B3, central wavelength 560 nm',
                  'B2, central wavelength 490 nm', 'B8, central wavelength 842 nm']
    test_img, _ = SyntheticImage(20, 18, 4, 'uint16', test_dir, 32640)\
        .create(pix_width=10, pix_height=10, valid_desc=valid_desc, seed=45)
    dsr = rasterio.open(test_img)
    dsr_x, dsr_y = s_2.to_xy(lon=1, lat=40, data=dsr)

    assert dsr_x == dsr_x_exm
    assert dsr_y == dsr_y_exm


def test_get_utm():
    """
    This method check the get_utm methods.
    """
    utm_exm = 'epsg:32640'
    test_dir = Path(tempfile.mkdtemp())
    valid_desc = ['B4, central wavelength 665 nm', 'B3, central wavelength 560 nm',
                  'B2, central wavelength 490 nm', 'B8, central wavelength 842 nm']
    test_img, _ = SyntheticImage(20, 18, 4, 'uint16', test_dir, 32640)\
        .create(pix_width=10, pix_height=10, valid_desc=valid_desc, seed=45)
    dsr = rasterio.open(test_img)
    dsr_utm = Superresolution.get_utm(dsr)

    assert dsr_utm == utm_exm


# pylint: disable-msg=too-many-locals
def test_area_of_interest():
    """
    this method checks the area_of_interest methods.
    """
    dsr_xmin_exm, dsr_ymin_exm, dsr_xmax_exm, dsr_ymax_exm, dsr_area_exm = (0, 0, 11, 11, 144)
    params = {'roi_x_y': [5, 5, 15, 15]}
    s_2 = Superresolution(params)

    test_dir = Path(tempfile.mkdtemp())
    valid_desc = ['B4, central wavelength 665 nm', 'B3, central wavelength 560 nm',
                  'B2, central wavelength 490 nm', 'B8, central wavelength 842 nm']
    test_img, _ = SyntheticImage(40, 40, 4, 'uint16', test_dir, 32640)\
        .create(pix_width=10, pix_height=10, valid_desc=valid_desc, seed=45)
    dsr = rasterio.open(test_img)
    dsr_xmin, dsr_ymin, dsr_xmax, dsr_ymax, dsr_area = s_2.area_of_interest(dsr)

    assert dsr_xmin == dsr_xmin_exm
    assert dsr_ymin == dsr_ymin_exm
    assert dsr_xmax == dsr_xmax_exm
    assert dsr_ymax == dsr_ymax_exm
    assert dsr_area == dsr_area_exm


def test_validate_description():
    """
    this method checks the validate_description methods.
    """
    valid_desc_exm = ['B4 (665 nm)', 'B3 (560 nm)', 'B2 (490 nm)', 'B8 (842 nm)']

    test_dir = Path(tempfile.mkdtemp())
    valid_desc = ['B4, central wavelength 665 nm', 'B3, central wavelength 560 nm',
                  'B2, central wavelength 490 nm', 'B8, central wavelength 842 nm']
    test_img, _ = SyntheticImage(20, 18, 4, 'uint16', test_dir)\
        .create(pix_width=10, pix_height=10, valid_desc=valid_desc, seed=45)
    dsr = rasterio.open(test_img)
    valid_desc = []
    print(dsr.count)
    for i in range(dsr.count):
        valid_desc.append(Superresolution.validate_description(dsr.descriptions[i]))

    assert set(valid_desc) == set(valid_desc_exm)


def test_get_band_short_name():
    """
    This method checks the functionality of get_short_name methods.
    """
    short_desc_exm = ['B4', 'B3', 'B2', 'B8']

    test_dir = Path(tempfile.mkdtemp())
    valid_desc = ['B4, central wavelength 665 nm', 'B3, central wavelength 560 nm',
                  'B2, central wavelength 490 nm', 'B8, central wavelength 842 nm']
    test_img, _ = SyntheticImage(20, 18, 4, 'uint16', test_dir)\
        .create(pix_width=10, pix_height=10, valid_desc=valid_desc, seed=45)
    dsr = rasterio.open(test_img)
    short_desc = []

    for i in range(dsr.count):
        desc = Superresolution.validate_description(dsr.descriptions[i])
        short_desc.append(Superresolution.get_band_short_name(desc))

    assert set(short_desc) == set(short_desc_exm)


# pylint: disable-msg=too-many-locals
def test_validate():
    """
    This method check whether validate function defined in the s2_tiles_supres
    file produce the correct results.
    """
    params = {'roi_x_y': [5, 5, 15, 15]}
    s_2 = Superresolution(params)

    test_dir = Path(tempfile.mkdtemp())
    valid_desc_10 = ['B4, central wavelength 665 nm', 'B3, central wavelength 560 nm',
                     'B2, central wavelength 490 nm', 'B8, central wavelength 842 nm']
    test_img_10, _ = SyntheticImage(20, 18, 4, 'uint16', test_dir)\
        .create(pix_width=10, pix_height=10, valid_desc=valid_desc_10, seed=45)
    ds10r = rasterio.open(test_img_10)

    validated_10m_indices_exm = [0, 1, 2, 3]
    validated_10m_bands_exm = ['B2', 'B3', 'B4', 'B8']
    validated_10m_bands, validated_10m_indices, _ = s_2.validate(data=ds10r)

    assert set(validated_10m_bands) == set(validated_10m_bands_exm)
    assert validated_10m_indices == validated_10m_indices_exm


def test_data_final():
    """
    This method checks the functionality of data_final method.
    """
    test_dir = Path(tempfile.mkdtemp())
    valid_desc = ['B4, central wavelength 665 nm', 'B3, central wavelength 560 nm',
                  'B2, central wavelength 490 nm', 'B8, central wavelength 842 nm']
    valid_indices = [0, 1, 2, 3]
    test_img, _ = SyntheticImage(20, 18, 4, 'uint16', test_dir) \
        .create(pix_width=10, pix_height=10, valid_desc=valid_desc, seed=45)
    dsr = rasterio.open(test_img)

    d_final = Superresolution.data_final(dsr, valid_indices, 0, 0, 5, 5, 1)
    assert d_final.shape == (6, 6, 4)


@pytest.fixture(scope="session", autouse=True)
@mock.patch.dict(os.environ, {"UP42_TASK_PARAMETERS": '{"roi_x_y": [5000, 5000, 5500, 5500]}'})
def superres_output() -> list:
    """
    This method initiates the Superresolution class from s2_tiles_supres and apply the run
    method on it to produce an output image.
    """
    params = load_params()  # type: dict
    Superresolution(params).run()
    for out_file in glob.iglob(os.path.join('/tmp/output/', '*.tif'), recursive=True):
        output_image_path = out_file
    for json_out_file in glob.iglob(os.path.join('/tmp/output/', '*.json'), recursive=True):
        output_json_path = json_out_file
    return [output_image_path, output_json_path]


# pylint: disable=redefined-outer-name
def test_output_transform(superres_output):
    """
    This method checks whether the outcome image has the correct 10m resolution for
    all the spectral bands.
    """
    output_image = rasterio.open(superres_output[0])
    assert output_image.transform[0] == 10
    assert output_image.transform[4] == -10


# pylint: disable=redefined-outer-name
def test_output_description(superres_output):
    """
    This method checks whether the outcome image has all the spectral bands for
    20m and 60m resolutions.
    """
    output_image = rasterio.open(superres_output[0])
    desc_exm = ('SR B5 (705 nm)', 'SR B6 (740 nm)',
                'SR B7 (783 nm)', 'SR B8A (865 nm)', 'SR B11 (1610 nm)',
                'SR B12 (2190 nm)', 'SR B1 (443 nm)', 'SR B9 (945 nm)')
    assert output_image.descriptions == desc_exm


# pylint: disable=redefined-outer-name
def test_output_projection(superres_output):
    """
    This method checks whether the outcome image has the correct georeference.
    """
    output_image = rasterio.open(superres_output[0])
    crs_exm = {'init': 'epsg:32640'}
    assert output_image.crs.to_dict() == crs_exm


def test_output_json_file(superres_output):
    """This method check whether the data.json of output image is created correctly."""
    with open(superres_output[1]) as f_p:
        data = json.loads(f_p.read())

    assert 'features' in [*data]
