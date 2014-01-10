#!/usr/bin/env python
# encoding: utf-8
"""
This file contains various helper functions used by all other modules.

@author: Sebastian Böck <sebastian.boeck@jku.at>

"""

import os.path
import glob
import warnings
import fnmatch

import numpy as np


def files(path, ext=None):
    """
    Returns a list of files in path matching the given extension.

    :param path: path or list of files to be filtered / searched
    :param ext:  only return files with this extension [default=None]
    :returns:    list of files

    """
    # determine the detection files
    if type(path) == list:
        # a list of files or paths is given
        file_list = []
        # recursively call the function
        for f in path:
            file_list.extend(files(f, ext))
    elif os.path.isdir(path):
        # use all files in the given path
        if ext is None:
            file_list = glob.glob("%s/*" % path)
        else:
            file_list = glob.glob("%s/*%s" % (path, ext))
    elif os.path.isfile(path):
        # no matchin needed
        if ext is None:
            file_list = [path]
        # file must have the correct extension
        elif path.endswith(ext):
            file_list = [path]
        # file does not match any condition
        else:
            file_list = []
    else:
        raise ValueError("only files or folders are supported.")
    # sort files
    file_list.sort()
    # return list
    return file_list


def stripext(filename, ext=None):
    """
    Strip of the extension.

    :param filename: filename to process
    :param ext:      strip of this extension
    :returns:        filename without extension

    """
    if ext is not None and filename.endswith(ext):
        return filename[:-len(ext)]
    return filename


def match_file(filename, match_list, ext=None, match_ext=None):
    """
    Match a file against a list of other files.

    :param filename:   file to be matched
    :param match_list: match to this list of files
    :param ext:        strip this extension from the file to match before
                       performing the search for matching files [default=None]
    :param match_ext:  only match files with this extension [default=None]
    :returns:          list of matched files

    """
    # get the base name without the path
    basename = os.path.basename(stripext(filename, ext))
    # init return list
    matches = []
    # look for files with the same base name in the files_list
    if match_ext is not None:
        pattern = "*%s*%s" % (basename, match_ext)
    else:
        pattern = "*%s" % basename
    for match in fnmatch.filter(match_list, pattern):
        # base names must match exactly
        if basename == os.path.basename(stripext(match, match_ext)):
            matches.append(match)
    # return the matches
    return matches


def load_events(filename):
    """
    Load a list of events from a text file, one floating point number per line.

    :param filename: name of the file or file handle
    :return:         numpy array of events

    """
    own_fid = False
    # open file if needed
    if isinstance(filename, basestring):
        fid = open(filename, 'rb')
        own_fid = True
    else:
        fid = filename
    try:
        # read in the events, one per line
        # 1st column is the event's time, the rest is ignored
        return np.fromiter((float(line.split(None, 1)[0]) for line in fid),
                dtype=np.double)
    finally:
        # close file if needed
        if own_fid:
            fid.close()


def write_events(events, filename):
    """
    Write a list of events to a text file, one floating point number per line.

    :param events:   list of events [seconds]
    :param filename: output file name or file handle

    """
    own_fid = False
    # open file if needed
    if isinstance(filename, basestring):
        fid = open(filename, 'wb')
        own_fid = True
    else:
        fid = filename
    try:
        fid.writelines('%g\n' % e for e in events)
    finally:
        # close file if needed
        if own_fid:
            fid.close()


def combine_events(events, delta):
    """
    Combine all events within a certain range.

    :param events: list of events [seconds]
    :param delta:  combination length [seconds]
    :return:       list of combined events

    """
    # return array if no events must be combined
    diff = np.diff(events)
    if not (events[1:][diff <= delta].any()):
        return events
    # array for combined events
    comb = []
    # copy the events, because the array is modified later
    events = np.copy(events)
    # iterate over all events
    idx = 0
    while idx < events.size - 1:
        # get the first event
        first = events[idx]
        # increase the events index
        idx += 1
        # get the second event
        second = events[idx]
        # combine the two events?
        if second - first <= delta:
            # two events within the combination window, combine them and
            # replace the second event in the original array with the mean
            # of the events
            events[idx] = (first + second) / 2.
        else:
            # the two events can not be combined,
            # store the first event in the new list
            comb.append(first)
    # always append the last element of the list
    comb.append(events[-1])
    # return the combined events
    return np.asarray(comb)


def quantize_events(events, fps, length=None):
    """
    Quantize the events.

    :param events: sequence of events [seconds]
    :param fps:    quantize with N frames per second
    :param length: length of the returned array [frames, default=last event]
    :returns:      a quantized numpy array

    """
    # length of the array
    if length is None:
        length = int(round(events[-1] * fps)) + 1
    # init array
    quantized = np.zeros(length)
    # set the events
    for event in events:
        idx = int(round(event * float(fps)))
        try:
            quantized[idx] = 1
        except IndexError:
            pass
    # return the events
    return quantized


def combine_activations(in_dirs, out_dir, ext='.activations', sep=''):
    """
    Quantize the activations of the given dirs.

    :param in_dirs: list of directories or files with activations
    :param out_dir: output directory
    :param ext:     extension for files [default='.activations']
    :param sep:     separator between activation values [default='']

    Note: The output directory must exist, existing files are overwritten.

          Empty (“”) separator means the file should be treated as binary;
          spaces (” ”) in the separator match zero or more whitespace;
          separator consisting only of spaces must match at least one
          whitespace.

          If out_dir is set and multiple network files contain the same
          files, the activations get averaged.

    """
    # get a list of activation files
    file_list = []
    for in_dir in in_dirs:
        file_list.extend(files(in_dir, ext))

    # get the base names of all files
    base_names = [os.path.basename(f) for f in file_list]
    # keep only unique names
    base_names = list(set(base_names))

    # combine all activations with the same base name
    for base_name in base_names:
        # get a list of all file matches
        matched_files = match_file(base_name, file_list)
        # init activations
        activations = None
        for matched_file in matched_files:
            if activations is None:
                activations = np.fromfile(matched_file, sep=sep)
            else:
                activations += np.fromfile(matched_file, sep=sep)
        # average activations
        if len(matched_files) > 1:
            activations /= len(matched_files)
        # output file
        if activations is not None:
            out_file = "%s/%s" % (out_dir, base_name)
            activations.tofile(out_file, sep)


# taken from: http://www.scipy.org/Cookbook/SegmentAxis
def segment_axis(a, length, overlap=0, axis=None, end='cut', endvalue=0):
    """
    Generate a new array that chops the given array along the given axis into
    overlapping frames.

    :param a:        array to segment
    :param length:   length of each frame
    :param overlap:  number of elements by which the frames should overlap
    :param axis:     axis to operate on; if None, act on the flattened array
    :param end:      what to do with the last frame, if the array is not evenly
                     divisible into pieces [default='cut']. possible values:
                     'cut'  simply discard the extra values
                     'wrap' copy values from the beginning of the array
                     'pad'  pad with a constant value
    :param endvalue: value to use for end='pad' [default=0]
    :returns:        2-d array with overlapping frames

    The array is not copied unless necessary (either because it is unevenly
    strided and being flattened or because end is set to 'pad' or 'wrap').

    Example:
    >>> segment_axis(arange(10), 4, 2)
    array([[0, 1, 2, 3],
           [2, 3, 4, 5],
           [4, 5, 6, 7],
           [6, 7, 8, 9]])

    """

    if axis is None:
        a = np.ravel(a)  # may copy
        axis = 0

    l = a.shape[axis]

    if overlap >= length:
        raise ValueError("frames cannot overlap by more than 100%.")
    if overlap < 0:
        raise ValueError("overlap must be nonnegative.")
    if length <= 0:
        raise ValueError("length must be positive.")

    if l < length or (l - length) % (length - overlap):
        if l > length:
            roundup = length + (1 + (l - length) // (length - overlap)) *\
                      (length - overlap)
            rounddown = length + ((l - length) // (length - overlap)) *\
                        (length - overlap)
        else:
            roundup = length
            rounddown = 0
        assert rounddown < l < roundup
        assert roundup == rounddown + (length - overlap) or\
               (roundup == length and rounddown == 0)
        a = a.swapaxes(-1, axis)

        if end == 'cut':
            a = a[..., :rounddown]
        elif end in ['pad', 'wrap']:
            # need to copy
            s = list(a.shape)
            s[-1] = roundup
            b = np.empty(s, dtype=a.dtype)
            b[..., :l] = a
            if end == 'pad':
                b[..., l:] = endvalue
            elif end == 'wrap':
                b[..., l:] = a[..., :roundup - l]
            a = b

        a = a.swapaxes(-1, axis)

    l = a.shape[axis]
    if l == 0:
        raise ValueError("Not enough data points to segment array in 'cut' "\
                         "mode; try 'pad' or 'wrap'")
    assert l >= length
    assert (l - length) % (length - overlap) == 0
    n = 1 + (l - length) // (length - overlap)
    s = a.strides[axis]
    newshape = a.shape[:axis] + (n, length) + a.shape[axis + 1:]
    newstrides = a.strides[:axis] + ((length - overlap) * s, s) +\
                 a.strides[axis + 1:]

    try:
        return np.ndarray.__new__(np.ndarray, strides=newstrides,
                                  shape=newshape, buffer=a, dtype=a.dtype)
    except TypeError:
        warnings.warn("Problem with ndarray creation forces copy.")
        a = a.copy()
        # Shape doesn't change but strides does
        newstrides = a.strides[:axis] + ((length - overlap) * s, s) +\
                     a.strides[axis + 1:]
        return np.ndarray.__new__(np.ndarray, strides=newstrides,
                                  shape=newshape, buffer=a, dtype=a.dtype)
