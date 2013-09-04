#!/usr/bin/env python
# encoding: utf-8
"""
SuperFlux onset detection algorithm.

@author: Sebastian Böck <sebastian.boeck@jku.at>

"""


def parser():
    import argparse
    import cp.utils.params

    # define parser
    p = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description='''
    If invoked without any parameters, the software detects all onsets in
    the given input file and writes them to the output file with the SuperFlux
    algorithm described in:

    "Maximum Filter Vibrato Suppression for Onset Detection"
    by Sebastian Böck and Gerhard Widmer
    in Proceedings of the 16th International Conference on Digital Audio Effects
    (DAFx-13), Maynooth, Ireland, September 2013

    ''')
    # general options
    cp.utils.params.add_mirex_io(p)
    # add other argument groups
    cp.utils.params.add_audio_arguments(p, fps=200)
    cp.utils.params.add_spec_arguments(p)
    cp.utils.params.add_filter_arguments(p, bands=24, norm_filter=False)
    cp.utils.params.add_log_arguments(p, mul=1, add=1)
    cp.utils.params.add_spectral_odf_arguments(p)
    cp.utils.params.add_onset_arguments(p)
    # version
    p.add_argument('--version', action='version', version='SuperFlux.2013')
    # parse arguments
    args = p.parse_args()
    # switch to offline mode
    if args.norm:
        args.online = False
        args.post_avg = 0
        args.post_max = 0
    # print arguments
    if args.verbose:
        print args
    # return
    return args


def main():
    from cp.audio.wav import Wav
    from cp.audio.spectrogram import LogarithmicFilteredSpectrogram
    from cp.audio.onset_detection import SpectralODF, Onset

    # parse arguments
    args = parser()

    # create a Wav object
    w = Wav(args.input, frame_size=args.window, online=args.online, mono=True, norm=args.norm, att=args.att, fps=args.fps)
    # create a Spectrogram object
    s = LogarithmicFilteredSpectrogram(w, mul=args.mul, add=args.add)
    # create an SpectralODF object and perform detection function on the object
    act = SpectralODF(s).superflux()
    # create an Onset object with the activations
    o = Onset(act, args.fps, args.online)
    # detect the onsets
    o.detect(args.threshold, combine=args.combine, delay=args.delay, smooth=args.smooth,
             pre_avg=args.pre_avg, post_avg=args.post_avg, pre_max=args.pre_max, post_max=args.post_max)
    # write the onsets to output
    o.write(args.output)

if __name__ == '__main__':
    main()
