#!/usr/bin/env python
# encoding: utf-8
"""
This file contains note evaluation functionality.

@author: Sebastian Böck <sebastian.boeck@jku.at>

"""

import numpy as np


from .helpers import calc_errors
from .simple import Evaluation, SumEvaluation, MeanEvaluation
from .onsets import onset_evaluation


def load_notes(filename, delimiter=None):
    """
    Load a list of notes from file.

    :param filename:  name of the file
    :param delimiter: string used to separate values
    :return:          array with events

    Expected file format: onset_time, MIDI_note, [duration, [velocity]]

    """
    return np.loadtxt(filename, delimiter=delimiter)


def remove_duplicate_rows(data):
    """
    Remove duplicate rows of a numpy array.

    :param data: 2D numpy array
    :return:     same array with duplicate rows removed

    """
    # found at: http://pastebin.com/Ad6EgNjB
    order = np.lexsort(data.T)
    data = data[order]
    diff = np.diff(data, axis=0)
    unique = np.ones(len(data), 'bool')
    unique[1:] = (diff != 0).any(axis=1)
    return data[unique]


def note_evaluation(detections, targets, window):
    """
    Count the true and false detections of the given detections and targets.

    :param detections: array with detected notes
                       [[onset, MIDI note, duration, velocity]]
    :param targets:    array with target onsets (same format as detections)
    :param window:     detection window [seconds]
    :return:           tuple of tp, fp, tn, fn numpy arrays

    tp: array with true positive detections
    fp: array with false positive detections
    tn: array with true negative detections (this one is empty!)
    fn: array with false negative detections

    Note: the true negative array is empty, because we are not interested in
          this class, since it is magnitudes as big as the note class.

    """
    # TODO: extend to also evaluate the duration and velocity of notes
    #       until then only use the first two columns (onsets + pitch)
    detections = remove_duplicate_rows(detections[:, :2])
    targets = remove_duplicate_rows(targets[:, :2])
    # init TP, FP and FN lists
    tp = []
    fp = []
    fn = []
    # get a list of all notes
    notes = np.unique(np.concatenate((detections[:, 1],
                                      targets[:, 1]))).tolist()
    # iterate over all notes
    for note in notes:
        # perform normal onset detection on ech note
        det = detections[detections[:, 1] == note]
        tar = targets[targets[:, 1] == note]
        tp_, fp_, _, fn_ = onset_evaluation(det[:, 0], tar[:, 0], window)
        # convert returned arrays to lists and append the detections and
        # targets to the correct lists
        tp.extend(det[np.in1d(det[:, 0], tp_)].tolist())
        fp.extend(det[np.in1d(det[:, 0], fp_)].tolist())
        fn.extend(tar[np.in1d(tar[:, 0], fn_)].tolist())
    # transform them back to numpy arrays
    tp = np.asarray(sorted(tp))
    fp = np.asarray(sorted(fp))
    fn = np.asarray(sorted(fn))
    # check calculation
    assert len(tp) + len(fp) == len(detections), 'bad TP / FP calculation'
    assert len(tp) + len(fn) == len(targets), 'bad FN calculation'
    # return the arrays
    return tp, fp, np.zeros(0), fn

# default evaluation values
WINDOW = 0.025


# for note evaluation with Precision, Recall, F-measure use the Evaluation
# class and just define the evaluation function
# TODO: extend to also report the measures without octave errors
class NoteEvaluation(Evaluation):
    """
    Simple evaluation class for measuring Precision, Recall and F-measure of
    notes.

    """
    def __init__(self, detections, targets, window=WINDOW):
        super(NoteEvaluation, self).__init__()
        self.detections = detections
        self.targets = targets
        # evaluate
        numbers = note_evaluation(detections, targets, window)
        self._tp, self._fp, self._tn, self._fn = numbers

    @property
    def errors(self):
        """
        Absolute errors of all true positive detections relative to the closest
        targets.

        """
        if self._errors is None:
            if self.num_tp == 0:
                # FIXME: what is the error in case of no TPs
                self._errors = np.zeros(0)
            else:
                self._errors = calc_errors(self.tp[:, 0], self.targets[:, 0])
        return self._errors


def parser():
    """
    Create a parser and parse the arguments.

    :return: the parsed arguments

    """
    import argparse
    # define parser
    p = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, description="""
    The script evaluates a file or folder with detections against a file or
    folder with targets. Extensions can be given to filter the detection and
    target file lists.

    """)
    # files used for evaluation
    p.add_argument('files', nargs='*',
                   help='files (or folder) to be evaluated')
    # extensions used for evaluation
    p.add_argument('-d', dest='det_ext', action='store', default='.notes.txt',
                   help='extension of the detection files')
    p.add_argument('-t', dest='tar_ext', action='store', default='.notes',
                   help='extension of the target files')
    # parameters for evaluation
    p.add_argument('-w', dest='window', action='store', type=float,
                   default=0.025,
                   help='evaluation window (+/- the given size) '
                        '[seconds, default=%(default)s]')
    p.add_argument('--delay', action='store', type=float, default=0.,
                   help='add given delay to all detections [seconds]')
    p.add_argument('--tex', action='store_true',
                   help='format errors for use is .tex files')
    # verbose
    p.add_argument('-v', dest='verbose', action='count',
                   help='increase verbosity level')
    # parse the arguments
    args = p.parse_args()
    # print the args
    if args.verbose >= 2:
        print args
    # return
    return args


def main():
    """
    Simple note evaluation.

    """
    from ..utils.helpers import files, match_file

    # parse arguments
    args = parser()

    # get detection and target files
    det_files = files(args.files, args.det_ext)
    tar_files = files(args.files, args.tar_ext)
    # quit if no files are found
    if len(det_files) == 0:
        print "no files to evaluate. exiting."
        exit()

    # sum and mean evaluation for all files
    sum_eval = SumEvaluation()
    mean_eval = MeanEvaluation()
    # evaluate all files
    for det_file in det_files:
        # get the detections file
        detections = load_notes(det_file)
        # get the matching target files
        matches = match_file(det_file, tar_files, args.det_ext, args.tar_ext)
        # quit if any file does not have a matching target file
        if len(matches) == 0:
            print " can't find a target file found for %s. exiting." % det_file
            exit()
        if len(matches) > 1:
            print " found more than 1 target file for %s. exiting." % det_file
            exit()
        if args.verbose:
            print det_file
        # load the targets
        targets = load_notes(matches[0])
        # shift the detections if needed
        if args.delay != 0:
            detections[:, 0] += args.delay
        # add the NoteEvaluation to mean evaluation
        ne = NoteEvaluation(detections, targets, window=args.window)
        # process the next target file
        # print stats for each file
        if args.verbose:
            ne.print_errors(args.tex)
        # add this file's mean evaluation to the global evaluation
        sum_eval += ne
        mean_eval += ne
        # process the next detection file
    # print summary
    print 'sum for %i files:' % (len(det_files))
    sum_eval.print_errors(args.tex)
    print 'mean for %i files:' % (len(det_files))
    mean_eval.print_errors(args.tex)

if __name__ == '__main__':
    main()
