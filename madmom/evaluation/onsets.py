#!/usr/bin/env python
# encoding: utf-8
"""
This file contains onset evaluation functionality.

It is described in:

"Evaluating the Online Capabilities of Onset Detection Methods"
by Sebastian Böck, Florian Krebs and Markus Schedl
in Proceedings of the 13th International Society for Music Information
Retrieval Conference (ISMIR), 2012

@author: Sebastian Böck <sebastian.boeck@jku.at>

"""

import numpy as np

from .simple import Evaluation, SumEvaluation, MeanEvaluation


# evaluation function for onset detection
def count_errors(detections, targets, window):
    """
    Count the true and false detections of the given detections and targets.

    :param detections: array with detected onsets [seconds]
    :param targets:    array with target onsets [seconds]
    :param window:     detection window [seconds]
    :return:           tuple of tp, fp, tn, fn numpy arrays

    tp: array with true positive detections
    fp: array with false positive detections
    tn: array with true negative detections (this one is empty!)
    fn: array with false negative detections

    Note: the true negative array is empty, because we are not interested in
          this class, since it is ~20 times as big as the onset class.

    """
    # sort the detections and targets
    det = detections.tolist()
    tar = targets.tolist()
    # cache variables
    det_length = len(detections)
    tar_length = len(targets)
    det_index = 0
    tar_index = 0
    # arrays for collecting the detections
    tp = []
    fp = []
    fn = []
    while det_index < det_length and tar_index < tar_length:
        # fetch the first detection
        d = det[det_index]
        # fetch the first target
        t = tar[tar_index]
        # shift with delay
        if abs(d - t) <= window:
            # TP detection
            tp.append(d)
            # increase the detection and target index
            det_index += 1
            tar_index += 1
        elif d < t:
            # FP detection
            fp.append(d)
            # increase the detection index
            det_index += 1
            # do not increase the target index
        elif d > t:
            # we missed a target, thus FN
            fn.append(t)
            # do not increase the detection index
            # increase the target index
            tar_index += 1
    # the remaining detections are FP
    fp.extend(det[det_index:])
    # the remaining targets are FN
    fn.extend(tar[tar_index:])
    # transform them back to numpy arrays
    tp = np.asarray(tp)
    fp = np.asarray(fp)
    fn = np.asarray(fn)
    # check calculation
    assert tp.size + fp.size == detections.size, 'bad TP / FP calculation'
    assert tp.size + fn.size == targets.size, 'bad FN calculation'
    # return the arrays
    return tp, fp, np.empty(0), fn


#def count_errors(detections, targets, window):
#    """
#    Count the true and false detections of the given detections and targets.
#
#    :param detections: array with detected onsets [seconds]
#    :param targets:    array with target onsets [seconds]
#    :param window:     detection window [seconds]
#    :return:           tuple of tp, fp, tn, fn numpy arrays
#
#    tp: array with true positive detections
#    fp: array with false positive detections
#    tn: array with true negative detections (this one is empty!)
#    fn: array with false negative detections
#
#    Note: the true negative array is empty, because we are not interested in
#          this class, since it is ~20 times as big as the onset class.
#
#    """
#     FIXME: is there a nice numpy like way to achieve the same behavior as above
#     i.e. detections and targets can match only once?
#    from .helpers import calc_absolute_errors
#    # no detections
#    if detections.size == 0:
#        # all targets are FNs
#        return np.empty(0), np.empty(0), np.empty(0), targets
#    # for TP & FP, calc the absolute errors of detections wrt. targets
#    errors = calc_absolute_errors(detections, targets)
#    # true positive detections
#    tp = detections[errors <= window]
#    # the remaining detections are FP
#    fp = detections[errors > window]
#    # for FN, calc the absolute errors of targets wrt. detections
#    errors = calc_absolute_errors(targets, detections)
#    fn = targets[errors > window]
#    # return the arrays
#    return tp, fp, np.empty(0), fn


# default values
WINDOW = 0.025


# for onset evaluation with Presicion, Recall, F-measure use the Evaluation
# class and just define the evaluation function
class OnsetEvaluation(Evaluation):
    """
    Simple class for measuring Precision, Recall and F-measure.

    """
    def __init__(self, detections, targets, window=WINDOW):
        super(OnsetEvaluation, self).__init__(detections, targets, count_errors, window=window)


class SumOnsetEvaluation(SumEvaluation):
    pass


class MeanOnsetEvaluation(MeanEvaluation):
    pass


def parser():
    import argparse
    # define parser
    p = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description="""
    The script evaluates a file or folder with detections against a file or
    folder with targets. Extensions can be given to filter the detection and
    target file lists.

    """)
    # files used for evaluation
    p.add_argument('detections', help='file (or folder) with detections to be evaluated (files being filtered according to the -d argument)')
    p.add_argument('targets', nargs='*', help='(multiple) file (or folder) with targets (files being filtered according to the -t argument)')
    # extensions used for evaluation
    p.add_argument('-d', dest='det_ext', action='store', default='.onsets.txt', help='extension of the detection files')
    p.add_argument('-t', dest='tar_ext', action='store', default='.onsets', help='extension of the target files')
    # parameters for evaluation
    p.add_argument('-w', dest='window', action='store', default=0.025, type=float, help='evaluation window (+/- the given size) [seconds, default=0.025]')
    p.add_argument('-c', dest='combine', action='store', default=0.03, type=float, help='combine target events within this range [seconds, default=0.03]')
    p.add_argument('--delay', action='store', default=0., type=float, help='add given delay to all detections [seconds]')
    p.add_argument('--tex', action='store_true', help='format errors for use is .tex files')
    # verbose
    p.add_argument('-v', dest='verbose', action='count', help='increase verbosity level')
    # parse the arguments
    args = p.parse_args()
    # print the args
    if args.verbose >= 2:
        print args
    # return
    return args


def main():
    from ..utils.helpers import files, match_file, load_events, combine_events

    # parse arguments
    args = parser()

    # get detection and target files
    det_files = files(args.detections, args.det_ext)
    if not args.targets:
        args.targets = args.detections

    # sum and mean evaluation for all files
    sum_eval = SumOnsetEvaluation()
    mean_eval = MeanOnsetEvaluation()

    # evaluate all files
    for det_file in det_files:
        # get the detections file
        detections = load_events(det_file)
        # get the matching target files
        tar_files = match_file(det_file, args.targets, args.det_ext, args.tar_ext)
        if len(tar_files) == 0:
            continue
        # do a mean evaluation with all matched target files
        me = MeanOnsetEvaluation()
        for tar_file in tar_files:
            # load the targets
            targets = load_events(tar_file)
            # combine the targets if needed
            if args.combine > 0:
                targets = combine_events(targets, args.combine)
            # shift the detections if needed
            if args.delay != 0:
                detections += args.delay
            # add the OnsetEvaluation to mean evaluation
            me += OnsetEvaluation(detections, targets, window=args.window)
            # process the next target file
        # print stats for each file
        if args.verbose:
            me.print_errors(args.tex)
        # add the resulting sum counter
        sum_eval += me
        mean_eval += me
        # process the next detection file
    # print summary
    print 'sum for %i files:' % (len(det_files))
    sum_eval.print_errors(args.tex)
    print 'mean for %i files:' % (len(det_files))
    mean_eval.print_errors(args.tex)

if __name__ == '__main__':
    main()
