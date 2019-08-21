# -*- coding: utf-8 -*-
"""
Created on Wed Aug 21 16:25:06 2019

@author: tageldim
"""

import numpy as np
from pandas import DataFrame, concat
import cv2
from shapely.geometry.polygon import Polygon
from PIL import Image

# %% =====================================================================


class Conditional_Print(object):
    """Print to screen if certain conditions are satisfied (Internal)."""

    def __init__(self, verbose=True):
        """Init. This is for PEP compliance."""
        self.verbose = verbose

    def _print(self, text):
        if self.verbose:
            print(text)

# %% =====================================================================


def _get_mask_offsets_from_masknames(maskpaths):
    """Get dictionary of mask offsets (top and left) (Internal).

    The pattern _left-123_ and _top-123_ is assumed to
    encode the x and y offset of the mask at base magnification.

    Arguments:
    -----------
    maskpaths : list
        names of masks (list of str)

    Returns:
    ----------
    dict
        indexed by maskname, each entry is a dict with keys top and left.

    """
    roi_offsets = dict()
    for maskpath in maskpaths:
        maskname = os.path.split(maskpath)[1]
        roi_offsets[maskname] = {
            'left': int(maskname.split('_left-')[1].split('_')[0]),
            'top': int(maskname.split('_top-')[1].split('_')[0]),
        }
    return roi_offsets

# %% =====================================================================


def get_roi_bboxes(maskpaths, roi_offsets=None):
    """Get dictionary of roi bounding boxes.

    Arguments:
    -----------
    maskpaths : list
        names of masks (list of str)
    roi_offsets : dict (default, None)
        dict indexed by maskname, each entry is a dict with keys
        top and left each is an integer. If None, then the pattern
        _left-123_ and _top-123_ is assumed to encode the x and y
        offset of the mask (i.e. inferred from mask name)

    Returns:
    ----------
    dict
        dict indexed by maskname, each entry is a dict with keys
        top, left, bottom, right, all of which are integers

    """
    if roi_offsets is not None:
        roiinfos = roi_offsets.copy()
    else:
        # get offset for all rois. This result is a dict that is indexed
        # by maskname, each entry is a dict with keys 'top' and 'left'.
        roiinfos = _get_mask_offsets_from_masknames(maskpaths)

    for maskpath in maskpaths:
        # Note: the following method does NOT actually load the mask
        # but just uses pillow to get its metadata. See:
        # https://stackoverflow.com/questions/15800704/ ...
        # ... get-image-size-without-loading-image-into-memory
        mask_obj = Image.open(maskpath, mode='r')
        width, height = mask_obj.size
        maskname = os.path.split(maskpath)[1]
        roiinfos[maskname]['right'] = roiinfos[maskname]['left'] + width
        roiinfos[maskname]['bottom'] = roiinfos[maskname]['top'] + height

    return roiinfos

# %% =====================================================================


def _get_roi_pairs(roinames):
    """Get unique roi pairs (Internal)."""
    ut = np.triu_indices(len(roinames), k=1)
    roi_pairs = []
    for pairidx in range(len(ut[0])):
        roi_pairs.append((ut[0][pairidx], ut[1][pairidx]))
    return roi_pairs

# %% =====================================================================


def _get_shared_roi_edges(roiinfos):
    """Get shared edges between rois in same slide (Internal)."""
    roinames = list(roiinfos.keys())
    edgepairs = [
        ('left', 'right'), ('right', 'left'),
        ('top', 'bottom'), ('bottom', 'top'),
    ]
    roi_pairs = _get_roi_pairs(roinames)

    # init shared edges
    shared_edges = DataFrame(columns=[
            'roi1-name', 'roi1-edge', 'roi2-name', 'roi2-edge'])

    for roi_pair in roi_pairs:
        roi1name = roinames[roi_pair[0]]
        roi2name = roinames[roi_pair[1]]
        idx = shared_edges.shape[0]
        for edgepair in edgepairs:
            # check if they share bounds for one edge
            if np.abs(
                  roiinfos[roi1name][edgepair[0]]
                  - roiinfos[roi2name][edgepair[1]]) < 2:
                # ensure they overlap in location along other axis
                if 'left' in edgepair:
                    start, end = ('top', 'bottom')
                else:
                    start, end = ('left', 'right')
                realStart = np.min(
                    (roiinfos[roi1name][start], roiinfos[roi2name][start]))
                realEnd = np.max(
                    (roiinfos[roi1name][end], roiinfos[roi2name][end]))
                length = realEnd - realStart
                nonoverlap_length = (
                    roiinfos[roi1name][end] - roiinfos[roi1name][start]) + (
                    roiinfos[roi2name][end] - roiinfos[roi2name][start])
                if length < nonoverlap_length:
                    shared_edges.loc[idx, 'roi1-name'] = roi1name
                    shared_edges.loc[idx, 'roi1-edge'] = edgepair[0]
                    shared_edges.loc[idx, 'roi2-name'] = roi2name
                    shared_edges.loc[idx, 'roi2-edge'] = edgepair[1]

    return shared_edges

# %%===========================================================================
# Constants & prep work
# =============================================================================

import os
import girder_client
from pandas import read_csv

APIURL = 'http://candygram.neurology.emory.edu:8080/api/v1/'
SAMPLE_SLIDE_ID = '5d586d76bd4404c6b1f286ae'

gc = girder_client.GirderClient(apiUrl=APIURL)
# gc.authenticate(interactive=True)
gc.authenticate(apiKey='kri19nTIGOkWH01TbzRqfohaaDWb6kPecRqGmemb')

# read GTCodes dataframe
PTESTS_PATH = os.path.join(os.getcwd(), '..', '..', 'plugin_tests')
GTCODE_PATH = os.path.join(PTESTS_PATH, 'test_files', 'sample_GTcodes.csv')
GTCodes_df = read_csv(GTCODE_PATH)
GTCodes_df.index = GTCodes_df.loc[:, 'group']

# This is where masks for adjacent rois are saved
MASK_LOADPATH = os.path.join(
    PTESTS_PATH, 'test_files', 'polygon_merger_roi_masks')
maskpaths = [
    os.path.join(MASK_LOADPATH, j) for j in os.listdir(MASK_LOADPATH)
    if j.endswith('.png')]

# %%===========================================================================

# get bounding mox coordinates for masks
roiinfos = get_roi_bboxes(maskpaths)

# get shared edges between masks
# shared_edges = _get_shared_roi_edges(roiinfos)








