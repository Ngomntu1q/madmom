#!/usr/bin/env python
# encoding: utf-8
"""
Script for correcting ground truth annotations in multiple fashions.

@author: Sebastian Böck <sebastian.boeck@jku.at>

"""

import numpy as np
import argparse

from madmom.utils import files, match_file


def main():
    """
    Simple annotation correction tool.

    """
    # define parser
    p = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, description="""
    The script corrects ground truth annotations.

    """)
    # files used for evaluation
    p.add_argument('files', nargs='*',
                   help='files (or folder) to be corrected')
    p.add_argument('--ext', default=['.onsets', '.beats'],
                   help='file extension of the ground-truth files')
    # output directory
    p.add_argument('-o', dest='output', default=None,
                   help='output directory')

    # annotations correction methods
    g = p.add_argument_group('timestamp correction methods')
    g.add_argument('--smooth', default=None, type=float,
                   help='smooth the annotations [seconds]')
    g.add_argument('--quantise', default=None, type=float,
                   help='quantise the annotations (seconds or extension of '
                        'the file with quantisation timestamps, e.g. beats or '
                        'onsets)')
    g.add_argument('--offset', default='.offset',
                   help='extension of the offsets files (shift + stretch)')
    g.add_argument('--shift', default=None, type=float,
                   help='shift the annotations [seconds]')
    g.add_argument('--stretch', default=None, type=float,
                   help='stretch the annotations [factor]')
    # verbose
    p.add_argument('-v', dest='verbose', action='count',
                   help='increase verbosity level')
    # parse the arguments
    args = p.parse_args()
    # print the args
    if args.verbose >= 2:
        print args

    # correct all files
    for infile in files(args.files, args.ext):
        if args.verbose:
            print infile

        # offset
        if args.offset:
            if isinstance(args.offset, basestring):
                # get the offset from a file
                correct = match_file(infile, args.files, ext=args.ext,
                                     match_ext=args.offset)[0]
                with open(correct, 'rb') as cf:
                    for l in cf:
                        # sample line: 0.0122817938+0.9999976816*T
                        shift, stretch = l.split('+')
                        args.shift = float(shift)
                        args.stretch = float(stretch.split('*')[0])
        # smooth
        if args.smooth:
            raise NotImplementedError
        # quantise
        quantised = args.quantise
        if args.quantise:
            if isinstance(args.shift, basestring):
                # get the quantisation timestamps from a file
                correct = match_file(infile, args.files, ext=args.ext,
                                     match_ext=args.quantise)[0]
                # quantised timestamps
                quantised = []
                with open(correct, 'rb') as cf:
                    for l in cf:
                        # skip comments
                        if l.startswith('#'):
                            continue
                        # get all new timestamps
                        else:
                            # first column should be the timestamp
                            quantised.append(l.split()[0])
                        quantised = np.asarray(quantised)

        # write the corrected file
        with open("%s.corrected" % infile, 'wb') as o:
            # process all events in the ground-truth file
            with open(infile) as i:
                for l in i:
                    # strip line
                    l.strip()
                    # skip comments
                    if l.startswith('#'):
                        # copy comments as is
                        o.write('%s\n' % l)
                    # alter the first column
                    # TODO: extend to alter all timestamp columns
                    else:
                        rest = None
                        try:
                            # extract the timestamp
                            timestamp, rest = l.split()
                            timestamp = float(timestamp)
                        except ValueError:
                            # only a timestamp given
                            timestamp = float(l)
                        # stretch
                        if args.stretch:
                            timestamp *= args.stretch
                        # shift
                        if args.shift:
                            timestamp += args.shift
                        # quantise
                        if isinstance(quantised, np.ndarray):
                            # get the closest match
                            timestamp = quantised[np.argmin(np.abs(quantised -
                                                                   timestamp))]
                        elif isinstance(quantised, float):
                            # set to the grid with the given resolution
                            timestamp /= quantised
                            timestamp = np.round(timestamp)
                            timestamp *= quantised

                        # skip negative timestamps
                        if timestamp < 0:
                            continue

                        # write the new timestamp
                        if rest:
                            o.write('%s\t%s\n' % (timestamp, rest))
                        else:
                            o.write('%s\n' % timestamp)


if __name__ == '__main__':
    main()
