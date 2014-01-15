#!/usr/bin/env python
# encoding: utf-8
"""
Copyright (c) 2012-2013 Sebastian Böck <sebastian.boeck@jku.at>

Redistribution in any form is not permitted!
"""

import os
import glob
import numpy as np
import multiprocessing as mp

from madmom.audio.wav import Wav
from madmom.audio.spectrogram import LogFiltSpec
from madmom.features.onsets import Onset
from madmom.ml.rnn import RecurrentNeuralNetwork

# set the path to saved neural networks and generate lists of NN files
NN_PATH = '%s/../madmom/ml/data' % (os.path.dirname(__file__))
NN_FILES = glob.glob("%s/onsets_brnn*npz" % NN_PATH)

# TODO: this information should be included/extracted in/from the NN files
FPS = 100
BANDS_PER_OCTAVE = 6
MUL = 5
ADD = 1
FMIN = 27.5
FMAX = 18000
RATIO = 0.25
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
    If invoked without any parameters, the software detects all onsets in the
    given input (file) and writes them to the output (file).
    ''')
    # mirex options
    madmom.utils.params.mirex(p)
    # add other argument groups
    p.add_argument('--nn_files', action='append', type=str, default=NN_FILES,
                   help='use these pre-trained neural networks '
                        '(multiple files can be given, one per argument)')
    p.add_argument('--threads', action='store', type=int, default=None,
                   help='number of parallel threads to run [default=number of '
                        'CPUs]')
    madmom.utils.params.audio(p, norm=False)
    madmom.utils.params.onset(p, threshold=0.35, combine=0.03, smooth=0.07,
                              pre_avg=0, post_avg=0, pre_max=1. / FPS,
                              post_max=1. / FPS)
    madmom.utils.params.io(p)
    # version
    p.add_argument('--version', action='version', version='OnsetDetector.2013')
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


def process(network, data):
    """
    Create a RNN and activate it with the given.

    :param network: file with the RNN model
    :param data:    data to activate the RNN
    :return:        activations of the RNN

    """
    return RecurrentNeuralNetwork(network).activate(data)


def main():
    """OnsetDetector.2013"""

    # parse arguments
    args = parser()

    # load or create onset activations
    if args.load:
        # load activations
        o = Onset(args.input, args.fps, args.online, args.sep)
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

        # list to store the returned activations
        activations = []

        def collector(result):
            """
            Collect the results of the networks.

            :param result: result

            """
            activations.append(result)

        # init a pool of workers
        pool = mp.Pool(args.threads)
        # test the data against all saved neural networks
        for nn_file in args.nn_files:
            pool.apply_async(process, args=(nn_file, data), callback=collector)
        # wait until everything is done
        pool.close()
        pool.join()
        # collect and normalize activations
        act = np.mean(np.asarray(activations), axis=0)

        # create an Onset object with the activations
        o = Onset(act.ravel(), args.fps, args.online)

    # save onset activations or detect onsets
    if args.save:
        # save activations
        o.save_activations(args.output, sep=args.sep)
    else:
        # detect the onsets
        o.detect(args.threshold, combine=args.combine, delay=args.delay,
                 smooth=args.smooth, pre_avg=args.pre_avg,
                 post_avg=args.post_avg, pre_max=args.pre_max,
                 post_max=args.post_max)
        # write the onsets to output
        o.write(args.output)

if __name__ == '__main__':
    main()
