#!/usr/bin/env python
# encoding: utf-8
"""
Copyright (c) 2012-2013 Sebastian Böck <sebastian.boeck@jku.at>

Redistribution in any form is not permitted!
"""

import os
import glob
import numpy as np
import itertools as it
import multiprocessing as mp

from madmom.audio.wav import Wav
from madmom.audio.spectrogram import LogFiltSpec
from madmom.features.beats import Beat
from madmom.ml.rnn import RecurrentNeuralNetwork

# set the path to saved neural networks and generate lists of NN files
NN_PATH = '%s/../madmom/ml/data' % (os.path.dirname(__file__))
NN_FILES = glob.glob("%s/beats_blstm*npz" % NN_PATH)

# TODO: this information should be included/extracted in/from the NN files
FPS = 100
BANDS_PER_OCTAVE = 3
MUL = 1
ADD = 1
FMIN = 30
FMAX = 17000
RATIO = 0.5
NORM_FILTERS = True


def parser():
    """
    Create a parser and parse the arguments.

    :return: the parsed arguments
    """
    import argparse
    import madmom.utils.params

    # define parser
    p = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, description='''
    If invoked without any parameters, the software detects all beats in the
    given input (file) and writes them to the output (file).
    ''')
    # mirex options
    madmom.utils.params.mirex(p)
    # add other argument groups
    madmom.utils.params.nn(p)
    madmom.utils.params.audio(p, fps=None, norm=False, online=None,
                              window=None)
    madmom.utils.params.beat(p)
    madmom.utils.params.io(p)
    # version
    p.add_argument('--version', action='version', version='BeatDetector.2013')
    # parse arguments
    args = p.parse_args()
    # set some defaults
    args.fps = FPS
    args.online = False
    if args.nn_files is None:
        args.nn_files = NN_FILES
    args.threads = min(len(args.nn_files), max(1, args.threads))
    # print arguments
    if args.verbose:
        print args
    # return
    return args


def process((nn_file, data)):
    """
    Loads a RNN model from the given file (first tuple item) and passes the
    given numpy array of data through it (second tuple item).

    """
    return RecurrentNeuralNetwork(nn_file).activate(data)


def main():
    """BeatDetector.2013"""

    # parse arguments
    args = parser()

    # load or create onset activations
    if args.load:
        # load activations
        b = Beat(args.input, args.fps, args.online, args.sep)
    else:
        # exit if no NN files are given
        if not args.nn_files:
            raise SystemExit('no NN model(s) given')

        # create a Wav object
        w = Wav(args.input, mono=True, norm=args.norm, att=args.att)
        # 1st spec
        s = LogFiltSpec(w, frame_size=1024, fps=FPS,
                        bands_per_octave=BANDS_PER_OCTAVE, mul=MUL, add=ADD,
                        norm_filters=NORM_FILTERS)
        data = np.hstack((s.spec, s.pos_diff))
        # 2nd spec
        s = LogFiltSpec(w, frame_size=2048, fps=FPS,
                        bands_per_octave=BANDS_PER_OCTAVE, mul=MUL, add=ADD,
                        norm_filters=NORM_FILTERS)
        data = np.hstack((data, s.spec, s.pos_diff))
        # 3rd spec
        s = LogFiltSpec(w, frame_size=4096, fps=FPS,
                        bands_per_octave=BANDS_PER_OCTAVE, mul=MUL, add=ADD,
                        norm_filters=NORM_FILTERS)
        # stack the data
        data = np.hstack((data, s.spec, s.pos_diff))

        # init a pool of workers (if needed)
        map_ = map
        if args.threads != 1:
            map_ = mp.Pool(args.threads).map
        # compute predictions with all saved neural networks (in parallel)
        activations = map_(process, it.izip(args.nn_files, it.repeat(data)))

        # average activations if needed
        nn_files = len(args.nn_files)
        if nn_files > 1:
            act = sum(activations) / nn_files
        else:
            act = activations[0]

        # create an Beat object with the activations
        b = Beat(act.ravel(), args.fps, args.online)

    # save beat activations or detect beats
    if args.save:
        # save activations
        b.save_activations(args.output, sep=args.sep)
    else:
        # detect the beats
        b.detect(args.threshold, smooth=args.smooth, min_bpm=args.min_bpm,
                 max_bpm=args.max_bpm)
        # write the beats to output
        b.write(args.output)

if __name__ == "__main__":
    main()
