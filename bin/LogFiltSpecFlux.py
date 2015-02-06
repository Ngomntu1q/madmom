#!/usr/bin/env python
# encoding: utf-8
"""
LogFiltSpecFlux onset detection algorithm.

@author: Sebastian Böck <sebastian.boeck@jku.at>

"""

from madmom import IOProcessor
from madmom.utils import io_arguments
from madmom.audio.signal import SignalProcessor, FramedSignalProcessor
from madmom.audio.spectrogram import SpectrogramProcessor
from madmom.features import ActivationsProcessor
from madmom.features.onsets import (SpectralOnsetProcessor,
                                    OnsetDetectionProcessor)


def parser():
    """
    Create a parser and parse the arguments.

    :return: the parsed arguments

    """
    import argparse

    # define parser
    p = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, description='''
    If invoked without any parameters, the software detects all onsets in the
    given input file and writes them to the output file with the
    LogFiltSpecFlux algorithm introduced in:

    "Evaluating the Online Capabilities of Onset Detection Methods"
    Sebastian Böck, Florian Krebs and Markus Schedl
    Proceedings of the 13th International Society for Music Information
    Retrieval Conference (ISMIR), 2012.

    ''')
    # add arguments
    io_arguments(p)
    SignalProcessor.add_arguments(p, norm=False, att=0)
    FramedSignalProcessor.add_arguments(p, fps=100, online=False)
    SpectrogramProcessor.add_filter_arguments(p, bands=12, fmin=30, fmax=17000,
                                              norm_filters=False)
    SpectrogramProcessor.add_log_arguments(p, log=True, mul=1, add=1)
    SpectrogramProcessor.add_diff_arguments(p, diff_ratio=0.5)
    OnsetDetectionProcessor.add_arguments(p, threshold=1.6, pre_max=0.01,
                                          post_max=0.05, pre_avg=0.15,
                                          post_avg=0, combine=0.03, delay=0)
    ActivationsProcessor.add_arguments(p)
    # version
    p.add_argument('--version', action='version',
                   version='LogFiltSpecFlux.2014')
    # parse arguments
    args = p.parse_args()
    # switch to offline mode
    if args.norm:
        args.online = False
    # print arguments
    if args.verbose:
        print args
    # return
    return args


def main():
    """LogFiltSpecFlux.2014"""

    # parse arguments
    args = parser()

    # load or create beat activations
    if args.load:
        in_processor = ActivationsProcessor(mode='r', **vars(args))
    else:
        in_processor = SpectralOnsetProcessor(**vars(args))

    # save onset activations or detect onsets
    if args.save:
        out_processor = ActivationsProcessor(mode='w', **vars(args))
    else:
        out_processor = OnsetDetectionProcessor(**vars(args))

    # process everything
    IOProcessor(in_processor, out_processor).process(args.input, args.output)

if __name__ == '__main__':
    main()
