from __future__ import division

import argparse
import os
import re
import sys
from collections import defaultdict

import numpy as np
import rasterio
from rasterio.windows import Window
from supres import DSen2_20, DSen2_60

# from osgeo import gdal, osr

# This code is adapted from this repository http://nicolas.brodu.net/code/superres and is distributed under the same
# license.

parser = argparse.ArgumentParser(description="Perform super-resolution on Sentinel-2 with DSen2. Code based on superres"
                                             " by Nicolas Brodu.",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
#parser.add_argument("data_file",
#                    help="An input sentinel-2 data file. This can be either the original ZIP file, or the S2A[...].xml "
#                         "file in a SAFE directory extracted from that ZIP.")
parser.add_argument("output_file", nargs="?",
                    help="A target data file. See also the --save_prefix option, and the --output_file_format option "
                         "(default is GTiff).")
parser.add_argument("--roi_lon_lat", default="",
                    help="Sets the region of interest to extract, WGS84, decimal notation. Use this syntax: lon_1,"
                         "lat_1,lon_2,lat_2. The order of points 1 and 2 does not matter: the region of interest "
                         "extends to the min/max in each direction. "
                         "Example: --roi_lon_lat=-1.12132,44.72408,-0.90350,44.58646")
parser.add_argument("--roi_x_y", default="",
                    help="Sets the region of interest to extract as pixels locations on the 10m bands. Use this "
                         "syntax: x_1,y_1,x_2,y_2. The order of points 1 and 2 does not matter: the region of interest "
                         "extends to the min/max in each direction and to nearby 60m pixel boundaries.")
parser.add_argument("--list_bands", action="store_true",
                    help="List bands in the input file subdata set matching the selected UTM zone, and exit.")
parser.add_argument("--run_60", action="store_true",
                    help="Select which bands to process and include in the output file. If this flag is set it will "
                         "super-resolve the 20m and 60m bands (B1,B2,B3,B4,B5,B6,B7,B8,B8A,B9,B11,B12). If it is not "
                         "set it will only super-resolve the 20m bands (B2,B3,B4,B5,B6,B7,B8,B8A,B11,B12). Band B10 "
                         "is to noisy and is not super-resolved.")
parser.add_argument("--list_UTM", action="store_true",
                    help="List all UTM zones present in the input file, together with their coverage of the ROI in "
                         "10m x 10m pixels.")
parser.add_argument("--select_UTM", default="",
                    help="Select a UTM zone. The default is to select the zone with the largest coverage of the ROI.")
parser.add_argument("--list_output_file_formats", action="store_true",
                    help="If specified, list all supported raster output file formats declared by GDAL and exit. Some "
                         "of these formats may be inappropriate for storing Sentinel-2 multispectral data.")
parser.add_argument("--output_file_format", default="GTiff",
                    help="Speficies the name of a GDAL driver that supports file creation, like ENVI or GTiff. If no "
                         "such driver exists, or if the format is \"npz\", then save all bands instead as a compressed "
                         "python/numpy file")
parser.add_argument("--copy_original_bands", action="store_true",
                    help="The default is not to copy the original selected 10m bands into the output file in addition "
                         "to the super-resolved bands. If this flag is used, the output file may be used as a 10m "
                         "version of the original Sentinel-2 file.")
parser.add_argument("--save_prefix", default="",
                    help="If set, speficies the name of a prefix for all output files. Use a trailing / to save into a "
                         "directory. The default of no prefix will save into the current directory. "
                         "Example: --save_prefix result/")

args = parser.parse_args()
globals().update(args.__dict__)

# if list_output_file_formats:
#    dcount = gdal.GetDriverCount()
#    for didx in range(dcount):
#        driver = gdal.GetDriver(didx)
#        if driver:
#            metadata = driver.GetMetadata()
#        if (gdal.DCAP_CREATE in (driver and metadata) and metadata[gdal.DCAP_CREATE] == 'YES' and
#        gdal.DCAP_RASTER in metadata and metadata[gdal.DCAP_RASTER] == 'YES'):
#            name = driver.GetDescription()
#            if "DMD_LONGNAME" in metadata:
#                name += ": " + metadata["DMD_LONGNAME"]
#            else:
#                name = driver.GetDescription()
#            if "DMD_EXTENSIONS" in metadata: name += " (" + metadata["DMD_EXTENSIONS"] + ")"
#            print(name)
#    sys.exit(0)

if run_60:
    select_bands = 'B1,B2,B3,B4,B5,B6,B7,B8,B8A,B9,B11,B12'
else:
    select_bands = 'B2,B3,B4,B5,B6,B7,B8,B8A,B11,B12'

# convert comma separated band list into a list
select_bands = [x for x in re.split(',', select_bands)]

if roi_lon_lat:
    roi_lon1, roi_lat1, roi_lon2, roi_lat2 = [float(x) for x in re.split(',', roi_lon_lat)]
else:
    roi_lon1, roi_lat1, roi_lon2, roi_lat2 = -180, -90, 180, 90


ds10 = rasterio.open('10m.tiff')
ds20 = rasterio.open('20m.tif')
ds60 = rasterio.open('60m.tif')

# case where we have several UTM in the data set
# => select the one with maximal coverage of the study zone
utm_idx = 0
utm = select_UTM
all_utms = defaultdict(int)
xmin, ymin, xmax, ymax = 0, 0, 0, 0
largest_area = -1


def get_max_min(x1, y1, x2, y2):
    tmxmin = max(min(x1, x2, ds10.width - 1), 0)
    tmxmax = min(max(x1, x2, 0), ds10.width - 1)
    tmymin = max(min(y1, y2, ds10.height - 1), 0)
    tmymax = min(max(y1, y2, 0), ds10.height - 1)
    # enlarge to the nearest 60 pixel boundary for the super-resolution
    tmxmin = int(tmxmin / 6) * 6
    tmxmax = int((tmxmax + 1) / 6) * 6 - 1
    tmymin = int(tmymin / 6) * 6
    tmymax = int((tmymax + 1) / 6) * 6 - 1
    area = (tmxmax - tmxmin + 1) * (tmymax - tmymin + 1)
    return tmxmin,tmymin,tmxmax,tmymax, area


if roi_x_y:
    roi_x1, roi_y1, roi_x2, roi_y2 = [float(x) for x in re.split(',', roi_x_y)]
    xmin, ymin, xmax, ymax, area = get_max_min(roi_x1,roi_y1, roi_x2, roi_y2)
else:
    xmin, ymin, xmax, ymax = (0, 0, ds10.width, ds10.height)

#     else:
#         xoff, a, b, yoff, d, e = ds.GetGeoTransform()
#         srs = osr.SpatialReference()
#         srs.ImportFromWkt(ds.GetProjection())
#         srsLatLon = osr.SpatialReference()
#         srsLatLon.SetWellKnownGeogCS("WGS84");
#         ct = osr.CoordinateTransformation(srsLatLon, srs)
#
#
#         def to_xy(lon, lat):
#             (xp, yp, h) = ct.TransformPoint(lon, lat, 0.)
#             xp -= xoff
#             yp -= yoff
#             # matrix inversion
#             det_inv = 1. / (a * e - d * b)
#             x = (e * xp - b * yp) * det_inv
#             y = (-d * xp + a * yp) * det_inv
#             return (int(x), int(y))
#
#
#         x1, y1 = to_xy(roi_lon1, roi_lat1)
#         x2, y2 = to_xy(roi_lon2, roi_lat2)

#     area = (tmxmax - tmxmin + 1) * (tmymax - tmymin + 1)
#     print(area)
#     current_utm = dsdesc[dsdesc.find("UTM"):]
#     if area > all_utms[current_utm]:
#         all_utms[current_utm] = area
#     if current_utm == select_UTM:
#         xmin, ymin, xmax, ymax = tmxmin, tmymin, tmxmax, tmymax
#         utm_idx = tmidx
#         utm = current_utm
#         break
#     if area > largest_area:
#         xmin, ymin, xmax, ymax = tmxmin, tmymin, tmxmax, tmymax
#         largest_area = area
#         utm_idx = tmidx
#         utm = dsdesc[dsdesc.find("UTM"):]
# print(area)

utm = 'UTM 39N'
if list_UTM:
    print("List of UTM zones (with ROI coverage in pixels):")
    for u in all_utms:
        print("%s (%d)" % (u, all_utms[u]))
    sys.exit(0)
print("Selected UTM Zone:", utm)
print("Selected pixel region: xmin=%d, ymin=%d, xmax=%d, ymax=%d:" % (xmin, ymin, xmax, ymax))
print("Image size: width=%d x height=%d" % (xmax - xmin + 1, ymax - ymin + 1))

if xmax < xmin or ymax < ymin:
    print("Invalid region of interest / UTM Zone combination")
    sys.exit(0)


def validate_description(description):
    m = re.match("(.*?), central wavelength (\d+) nm", description)
    if m:
        return m.group(1) + " (" + m.group(2) + " nm)"
    # Some HDR restrictions... ENVI band names should not include commas
    if output_file_format == 'ENVI' and ',' in description:
        pos = description.find(',')
        return description[:pos] + description[(pos + 1):]
    return description


if list_bands:
    print("\n10m bands:")
    for b in range(0, ds10.count):
        print("- " + validate_description(ds10.descriptions[b]))
    print("\n20m bands:")
    for b in range(0, ds20.count):
        print("- " + validate_description(ds10.descriptions[b]))
    print("\n60m bands:")
    for b in range(0, ds60.count):
        print("- " + validate_description(ds10.descriptions[b]))
    print("")


def get_band_short_name(description):
    if ',' in description:
        return description[:description.find(',')]
    if ' ' in description:
        return description[:description.find(' ')]
    return description[:3]


def validate(data):
    validated_bands = []
    validated_indices = []
    validated_descriptions = defaultdict(str)
    for b in range(0, data.count):
        desc = validate_description(data.descriptions[b])
        name = get_band_short_name(desc)
        if name in select_bands:
            sys.stdout.write(" " + name)
            select_bands.remove(name)
            validated_bands += [name]
            validated_indices += [b]
            validated_descriptions[name] = desc
    return validated_bands, validated_indices, validated_descriptions


sys.stdout.write("Selected 10m bands:")
validated_10m_bands, validated_10m_indices, dic_10m = validate(ds10)

sys.stdout.write("Selected 20m bands:")
validated_20m_bands, validated_20m_indices, dic_20m = validate(ds20)

sys.stdout.write("Selected 60m bands:")
validated_60m_bands, validated_60m_indices, dic_60m = validate(ds60)

validated_descriptions_all = {**dic_10m, **dic_20m, **dic_60m}
# validated_10m_indices = [0, 1, 2, 3]
# validated_10m_bands = ['B2', 'B3', 'B4', 'B8']
# validated_20m_indices = [0, 1, 2, 3, 4, 5]
# validated_20m_bands = ['B5', 'B6', 'B7', 'B8A', 'B11', 'B12']
# validated_60m_indices = [0, 1, 2]
# validated_60m_bands = ['B1', 'B9', 'B10']

sys.stdout.write("\n")

if list_bands:
    sys.exit(0)

# All query options are processed, we now require an output file
#if not output_file:
#    print("Error: you must provide the name of an output file. I will set it identical to the input...")
#    output_file = os.path.split(data_file)[1] + '.tif'
    # sys.exit(1)

output_file = save_prefix + output_file
# Some HDR restrictions... ENVI file name should be the .bin, not the .hdr
if output_file_format == 'ENVI' and (output_file[-4:] == '.hdr' or output_file[-4:] == '.HDR'):
    output_file = output_file[:-4] + '.bin'

def data_final(data, term, x_mi, y_mi, x_ma, y_ma, n):
    if term:
        print(term)
        d_final = np.rollaxis(
            data.read(window=Window(col_off=x_mi, row_off=y_mi, width=x_ma - x_mi + n, height=y_ma - y_mi + n)), 0, 3)[
                 :, :, term]
    return d_final


if run_60:
    data10 = data_final(ds10, validated_10m_indices, xmin, ymin, xmax, ymax, 1)
    data20 = data_final(ds20, validated_20m_indices, xmin // 2, ymin // 2, xmax // 2, ymax // 2, 1 // 2)
    data60 = data_final(ds60, validated_60m_indices, xmin // 6, ymin // 6, xmax // 6, ymax // 6, 1 // 6)
else:
    data10 = data_final(ds10, validated_10m_indices, xmin, ymin, xmax, ymax, 1)
    data20 = data_final(ds20, validated_20m_indices, xmin // 2, ymin // 2, xmax // 2, ymax // 2, 1 // 2)

if validated_60m_bands and validated_20m_bands and validated_10m_bands:
    print("Super-resolving the 60m data into 10m bands")
    sr60 = DSen2_60(data10, data20, data60, deep=False)
else:
    sr60 = None

if validated_10m_bands and validated_20m_bands:
    print("Super-resolving the 20m data into 10m bands")
    sr20 = DSen2_20(data10, data20, deep=False)
else:
    sr20 = None

sr_band_names = []

if sr20 is None:
    print("No super-resolution performed, exiting")
    sys.exit(0)

# if output_file_format != "npz":
#    revert_to_npz = True
#    driver = gdal.GetDriverByName(output_file_format)
#    if driver:
#        metadata = driver.GetMetadata()
#        if gdal.DCAP_CREATE in metadata and metadata[gdal.DCAP_CREATE] == 'YES':
#            revert_to_npz = False
#    if revert_to_npz:
#        print("Gdal doesn't support creating %s files" % output_file_format)
#        print("Writing to npz as a fallback")
#        output_file_format = "npz"
#    bands = None
#else:
#    bands = dict()
#    result_dataset = None

#bidx = 0
#all_descriptions = []
#source_band = dict()


#def write_band_data(data, description, name=None):
#    global all_descriptions
#    global bidx
#    all_descriptions += [description]
#    if output_file_format == "npz":
#        bands[description] = data
#    else:
#        bidx += 1
#        result_dataset.GetRasterBand(bidx).SetDescription(description)
#        result_dataset.GetRasterBand(bidx).WriteArray(data)


if sr60 is not None:
    sr = np.concatenate((sr20, sr60), axis=2)
    validated_sr_bands = validated_20m_bands + validated_60m_bands
else:
    sr = sr20
    validated_sr_bands = validated_20m_bands

if copy_original_bands:
    out_dims = data10.shape[2] + sr.shape[2]
else:
    out_dims = sr.shape[2]

sys.stdout.write("Writing")
# result_dataset = driver.Create(output_file, data10.shape[1], data10.shape[0], out_dims, gdal.GDT_Float64)

print(" the super-resolved bands in %s" % output_file)
profile = ds10.profile
with rasterio.open('/tmp/example.tif', 'w' ,**profile) as ds10w:
    for bi, bn in enumerate(validated_sr_bands):
        profile.update(dtype=rasterio.float32)
        ds10w.write(sr20[:,:,bi], indexes=bi+1)


# Translate the image upper left corner. We multiply x10 to transform from pixel position in the 10m_band to meters.
# geot = list(ds10.GetGeoTransform())
# geot[0] += xmin * 10
# geot[3] -= ymin * 10
# result_dataset.SetGeoTransform(tuple(geot))
# result_dataset.SetProjection(ds10.GetProjection())

# result_dataset.(ds10.crs.wkt)

# if copy_original_bands:
#    sys.stdout.write(" the original 10m bands and")
    # Write the original 10m bands
#    for bi, bn in enumerate(validated_10m_bands):
#        write_band_data(data10[:, :, bi], validated_descriptions_all[bn])

print(" the super-resolved bands in %s" % output_file)
# for bi, bn in enumerate(validated_sr_bands):
#    write_band_data(sr[:, :, bi], "SR" + validated_descriptions_all[bn], "SR" + bn)

# for desc in all_descriptions:
#    print(desc)

if output_file_format == "npz":
    np.savez(output_file, bands=bands)
