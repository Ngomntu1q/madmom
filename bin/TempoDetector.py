#!/usr/bin/env python
# encoding: utf-8
"""
Copyright (c) 2012-2013 Sebastian Böck <sebastian.boeck@jku.at>

Redistribution in any form is not permitted!
"""

import os
import numpy as np

from cp.audio.wav import Wav
from cp.audio.spectrogram import LogFiltSpec
from cp.features.beats import Beat
from cp.utils.rnnlib import create_nc_file, test_nc_files, NN_BEAT_FILES

FPS = 100
BANDS_PER_OCTAVE = 3
MUL = 1
ADD = 1
FMIN = 30
FMAX = 17000
RATIO = 0.5
NORM_FILTER = True


def parser():
    import argparse
    import cp.utils.params

    # define parser
    p = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description='''
    If invoked without any parameters, the software detects the dominant tempi
    in the given input (file) and writes them to the output (file).
    ''')
    # mirex options
    cp.utils.params.add_mirex_io(p)
    # add other argument groups
    cp.utils.params.add_nn_arguments(p, nn_files=NN_BEAT_FILES)
    cp.utils.params.add_audio_arguments(p, fps=None, norm=False, online=None, window=None)
    cp.utils.params.add_beat_arguments(p, io=True)
    # version
    p.add_argument('--version', action='version', version='TempoDetector.2013')
    # parse arguments
    args = p.parse_args()
    # set some defaults
    args.fps = FPS
    args.online = False
    # print arguments
    if args.verbose:
        print args
    # return
    return args


def main():
    """TempoDetector.2013"""

    # parse arguments
    args = parser()

    # load or create onset activations
    if args.load:
        # load activations
        b = Beat(args.input, args.fps, args.online, args.sep)
    else:
        # create a Wav object
        w = Wav(args.input, fps=FPS, mono=True, norm=args.norm, online=False)
        # 1st spec
        w.frame_size = 1024
        s = LogFiltSpec(w, bands_per_octave=BANDS_PER_OCTAVE, mul=MUL, add=ADD, norm_filter=NORM_FILTER)
        nc_data = np.hstack((s.spec, s.pos_diff))
        # 2nd spec
        w.frame_size = 2048
        s = LogFiltSpec(w, bands_per_octave=BANDS_PER_OCTAVE, mul=MUL, add=ADD, norm_filter=NORM_FILTER)
        nc_data = np.hstack((nc_data, s.spec, s.pos_diff))
        # 3rd spec
        w.frame_size = 4096
        s = LogFiltSpec(w, bands_per_octave=BANDS_PER_OCTAVE, mul=MUL, add=ADD, norm_filter=NORM_FILTER)
        nc_data = np.hstack((nc_data, s.spec, s.pos_diff))
        # create a fake onset vector
        nc_targets = np.zeros(w.num_frames)
        nc_targets[0] = 1
        # create a .nc file
        create_nc_file(args.nc_file, nc_data, nc_targets)
        # test the file against all saved neural nets
        # Note: test_nc_files() always expects a list of .nc_files
        acts = test_nc_files([args.nc_file], args.nn_files, threads=args.threads, verbose=(args.verbose >= 2))
        # create an Onset object with the first activations of the list
        b = Beat(acts[0], args.fps, args.online)

    # save onset activations or detect onsets
    if args.save:
        # save activations
        b.save_activations(args.output, sep=args.sep)
    else:
        # detect the tempo
        t1, t2, weight = b.tempo(args.threshold, smooth=args.smooth, min_bpm=args.min_bpm, max_bpm=args.max_bpm, mirex=True)
        # write to output
        was_closed = False
        if not isinstance(args.output, file):
            # open the file if necessary
            args.output = open(args.output, 'w')
            was_closed = True
        args.output.write("%.2f\t%.2f\t%.2f\n" % (t1, t2, weight))
        # close the output again?
        if was_closed:
            args.output.close()

    # clean up
    os.remove(args.nc_file)

if __name__ == '__main__':
    main()
