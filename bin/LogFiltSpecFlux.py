#!/usr/bin/env python
# encoding: utf-8
"""
LogFiltSpecFlux onset detection algorithm.

@author: Sebastian Böck <sebastian.boeck@jku.at>

"""

import madmom.utils.params


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
    by Sebastian Böck, Florian Krebs and Markus Schedl
    in Proceedings of the 13th International Society for
    Music Information Retrieval Conference (ISMIR), 2012

    ''')
    # input/output options
    madmom.utils.params.io(p)
    # add other argument groups
    madmom.utils.params.audio(p, fps=100, online=False)
    madmom.utils.params.spec(p)
    madmom.utils.params.filtering(p, bands=12, norm_filters=False)
    madmom.utils.params.log(p, mul=1, add=1)
    madmom.utils.params.onset(p, threshold=2.75)
    madmom.utils.params.save_load(p)
    # version
    p.add_argument('--version', action='version',
                   version='LogFiltSpecFlux.2013')
    # parse arguments
    args = p.parse_args()
    # switch to offline mode
    if args.norm:
        args.online = False
        args.post_avg = 0
        args.post_max = 0
    # translate online/offline mode
    if args.online:
        args.origin = 'online'
    else:
        args.origin = 'offline'
    # print arguments
    if args.verbose:
        print args
    # return
    return args


def main():
    """LogFiltSpecFlux.2013"""
    from madmom.audio.wav import Wav
    from madmom.audio.spectrogram import LogFiltSpec
    from madmom.features.onsets import SpectralOnsetDetection, Onset

    # parse arguments
    args = parser()

    # load or create onset activations
    if args.load:
        # load activations
        o = Onset(args.input, args.fps, args.online, args.sep)
    else:
        # create a Wav object
        w = Wav(args.input, mono=True, norm=args.norm, att=args.att)
        # create a Spectrogram object
        s = LogFiltSpec(w, frame_size=args.window, origin=args.origin,
                        fps=args.fps, mul=args.mul, add=args.add,
                        norm_filters=args.norm_filters)
        # create an SpectralOnsetDetection object
        sod = SpectralOnsetDetection(s)
        # perform spectral flux
        act = sod.sf()
        # create an Onset object with the activations
        o = Onset(act, args.fps, args.online)

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
