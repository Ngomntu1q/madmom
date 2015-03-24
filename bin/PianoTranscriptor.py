#!/usr/bin/env python
# encoding: utf-8
"""
@author: Sebastian Böck <sebastian.boeck@jku.at>

"""

import argparse

from madmom.features.notes import RNNNoteTranscription
from madmom.utils import io_arguments


def main():
    """PianoTranscriptor.2014"""

    # define parser
    p = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, description='''
    The software detects all notes (onsets) in an audio file with the algorithm
    described in:

    "Polyphonic Piano Note Transcription with Recurrent Neural Networks"
    Sebastian Böck and Markus Schedl.
    Proceedings of the 37th International Conference on Acoustics, Speech and
    Signal Processing (ICASSP), 2012.

    Instead of 'LSTM' units, the current version uses 'tanh' units.

    ''')
    # version
    p.add_argument('--version', action='version',
                   version='PianoTranscriptor.2014')
    # add arguments
    io_arguments(p, suffix='.notes.txt')
    RNNNoteTranscription.add_arguments(p)
    # midi arguments
    # import madmom.utils.midi as midi
    # midi.MIDIFile.add_arguments(p, length=0.6, velocity=100)
    p.add_argument('--midi', dest='output_format', action='store_const',
                   const='midi', help='save as MIDI')
    # mirex stuff
    p.add_argument('--mirex', dest='output_format', action='store_const',
                   const='mirex', help='use the MIREX output format')

    # parse arguments
    args = p.parse_args()
    print args
    # set the suffix for midi files
    if args.output_format == 'midi':
        args.output_suffix = '.mid'
    # print arguments
    if args.verbose:
        print args

    # create a processor
    processor = RNNNoteTranscription(**vars(args))
    # and call the processing function
    args.func(processor, **vars(args))


if __name__ == '__main__':
    main()
