#!/usr/bin/env python
# encoding: utf-8
"""
@author: Filip Korzeniowski <filip.korzeniowski@jku.at>

"""

from madmom.utils import io_arguments
from madmom.features.beats import RNNBeatTracking, CRFBeatDetection


def parser():
    """
    Create a parser and parse the arguments.

    :return: the parsed arguments

    """
    import argparse

    # define parser
    p = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, description='''
    If invoked without any parameters, the software detects all beats in the
    given input (file) and writes them to the output (file) according to the
    method described in:

    "Probabilistic extraction of beat positions from a beat activation
     function"
    Filip Korzeniowski, Sebastian Böck and Gerhard Widmer
    In Proceedings of the 15th International Society for Music Information
    Retrieval Conference (ISMIR), 2014.

    ''')
    # add arguments
    io_arguments(p)
    RNNBeatTracking.add_activation_arguments(p)
    RNNBeatTracking.add_rnn_arguments(p)
    CRFBeatDetection.add_tempo_arguments(p)
    CRFBeatDetection.add_arguments(p)
    # version
    p.add_argument('--version', action='version', version='CRFBeatDetector')
    # parse arguments
    args = p.parse_args()
    # print arguments
    if args.verbose:
        print args
    # return
    return args


def main():
    """CRFBeatDetector."""

    # parse arguments
    args = parser()

    # create an processor
    processor = RNNBeatTracking(beat_method='CRFBeatDetection', **vars(args))
    # process everything
    processor.process(args.input, args.output)

if __name__ == "__main__":
    main()
