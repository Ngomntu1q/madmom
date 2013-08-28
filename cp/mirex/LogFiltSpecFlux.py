#!/usr/bin/env python
# encoding: utf-8
"""
Copyright (c) 2013 Sebastian Böck <sebastian.boeck@jku.at>
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import cp.utils.params


def parser():
    import argparse

    # define parser
    p = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description='''
    If invoked without any parameters, the software detects all onsets in
    the given input file and writes them to the output file with the SuperFlux
    algorithm introduced in:

    "Evaluating the Online Capabilities of Onset Detection Methods"
    by Sebastian Böck, Florian Krebs and Markus Schedl
    in Proceedings of the 13th International Society for
    Music Information Retrieval Conference (ISMIR), 2012

    ''')
    # general options
    cp.utils.params.add_mirex_io(p)
    # add other argument groups
    cp.utils.params.add_audio_arguments(p, fps=100)
    cp.utils.params.add_spec_arguments(p)
    cp.utils.params.add_filter_arguments(p, bands=12, norm_filter=False)
    cp.utils.params.add_log_arguments(p, mul=1, add=1)
    cp.utils.params.add_onset_arguments(p, threshold=2.75)
    # version
    p.add_argument('--version', action='version', version='LogFiltSpecFlux.2013')
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

    # create a wav object
    w = Wav(args.input, frame_size=args.window, online=args.online, mono=True, norm=args.norm, att=args.att, fps=args.fps)
    # create a spectrogram object
    s = LogarithmicFilteredSpectrogram(w, mul=args.mul, add=args.add)
    # create an SpectralODF object and perform detection function on the object
    act = SpectralODF(s).sf()
    # create an Onset object with the activations
    o = Onset(act, args.fps, args.online)
    # detect the onsets
    o.detect(args.threshold, combine=args.combine, delay=args.delay, pre_avg=args.pre_avg, post_avg=args.post_avg, pre_max=args.pre_max, post_max=args.post_max)
    # write the onsets to a file
    o.write(args.output)

if __name__ == '__main__':
    main()
