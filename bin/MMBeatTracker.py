#!/usr/bin/env python
# encoding: utf-8
"""
@author: Sebastian Böck <sebastian.boeck@jku.at>

"""

import argparse

from madmom.utils import io_arguments
from madmom.features.beats import RNNBeatTracking, DBNBeatTracking


def main():
    """MMBeatTracker"""

    # define parser
    p = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, description='''
    The software detects all beats in an audio file according to the method
    described in:

    "A multi-model approach to beat tracking considering heterogeneous music
     styles"
    Sebastian Böck, Florian Krebs and Gerhard Widmer
    Proceedings of the 15th International Society for Music Information
    Retrieval Conference (ISMIR), 2014.

    Instead of the originally proposed transition model for the DBN, the
    following is used:

    "An efficient state space model for joint tempo and meter tracking"
    Florian Krebs, Sebastian Böck and Gerhard Widmer
    Proceedings of the 16th International Society for Music Information
    Retrieval Conference (ISMIR), 2015.

    ''')
    # version
    p.add_argument('--version', action='version', version='MMBeatTracker.2015')
    # add arguments
    io_arguments(p, suffix='.beats.txt')
    RNNBeatTracking.add_activation_arguments(p)
    RNNBeatTracking.add_rnn_arguments(p)
    DBNBeatTracking.add_arguments(p)
    # parse arguments
    args = p.parse_args()
    # print arguments
    if args.verbose:
        print args

    # create a processor
    processor = RNNBeatTracking(beat_method='DBNBeatTracking',
                                multi_model=True, **vars(args))
    # and call the processing function
    args.func(processor, **vars(args))


if __name__ == '__main__':
    main()
