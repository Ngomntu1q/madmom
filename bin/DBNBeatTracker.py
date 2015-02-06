#!/usr/bin/env python
# encoding: utf-8
"""
@author: Sebastian Böck <sebastian.boeck@jku.at>

"""

from madmom import IOProcessor
from madmom.utils import io_arguments
from madmom.features import ActivationsProcessor
from madmom.features.beats import RNNBeatProcessor, DBNBeatTrackingProcessor


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

    "A multi-model approach to beat tracking considering heterogeneous music
     styles"
    Sebastian Böck, Florian Krebs and Gerhard Widmer
    Proceedings of the 15th International Society for Music Information
    Retrieval Conference (ISMIR 2014), 2014.

    It does not use the multi-model (Section 2.2.) and selection stage (Section
    2.3), i.e. this version corresponds to the pure DBN version of the
    algorithm for which results are given in Table 2.

    ''')

    # add arguments
    io_arguments(p)
    ActivationsProcessor.add_arguments(p)
    RNNBeatProcessor.add_arguments(p)
    DBNBeatTrackingProcessor.add_dbn_arguments(p)
    # version
    p.add_argument('--version', action='version', version='DBNBeatTracker')
    # parse arguments
    args = p.parse_args()
    # print arguments
    if args.verbose:
        print args
    # return
    return args


def main():
    """DBNBeatTracker"""

    # parse arguments
    args = parser()
    args.fps = 100

    # load or create beat activations
    if args.load:
        in_processor = ActivationsProcessor(mode='r', **vars(args))
    else:
        in_processor = RNNBeatProcessor(**vars(args))

    # save beat activations or detect beats
    if args.save:
        out_processor = ActivationsProcessor(mode='w', **vars(args))
    else:
        out_processor = DBNBeatTrackingProcessor(**vars(args))

    # process everything
    IOProcessor(in_processor, out_processor).process(args.input, args.output)



if __name__ == '__main__':
    main()
