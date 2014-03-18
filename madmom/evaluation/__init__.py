# encoding: utf-8
"""
Evaluation package.

All evaluation methods of this package can be used as scripts directly, if the
package is in $PYTHONPATH.

Example:

python -m madmom.evaluation.onsets /dir/to/be/evaluated

"""
import numpy as np


# evaluation helper functions
def find_closest_matches(detections, annotations):
    """
    Find the closest annotation for each detection.

    :param detections:  numpy array with the detected events [float, seconds]
    :param annotations: numpy array with the annotated events [float, seconds]
    :returns:           numpy array with indices of the closest matches [int]

    Note: The sequences must be ordered!

    """
    # if no detections or annotations are given
    if len(detections) == 0 or len(annotations) == 0:
        # return a empty array
        return np.zeros(0, dtype=np.int)
    # if only a single annotation is given
    if len(annotations) == 1:
        # return an array as long as the detections with indices 0
        return np.zeros(len(detections), dtype=np.int)
    # solution found at: http://stackoverflow.com/questions/8914491/
    indices = annotations.searchsorted(detections)
    indices = np.clip(indices, 1, len(annotations) - 1)
    left = annotations[indices - 1]
    right = annotations[indices]
    indices -= detections - left < right - detections
    # return the indices of the closest matches
    return indices


def calc_errors(detections, annotations, matches=None):
    """
    Errors of the detections relative to the closest annotations.

    :param detections:  numpy array with the detected events [float, seconds]
    :param annotations: numpy array with the annotated events [float, seconds]
    :param matches:     numpy array with indices of the closest events [int]
    :returns:           numpy array with the errors [seconds]

    Note: The sequences must be ordered! To speed up the calculation, a list
          of pre-computed indices of the closest matches can be used.

    """
    # if no detections or annotations are given
    if len(detections) == 0 or len(annotations) == 0:
        # return a empty array
        return np.zeros(0, dtype=np.float)
    # determine the closest annotations
    if matches is None:
        matches = find_closest_matches(detections, annotations)
    # calc error relative to those annotations
    errors = detections - annotations[matches]
    # return the errors
    return errors


def calc_absolute_errors(detections, annotations, matches=None):
    """
    Absolute errors of the detections relative to the closest annotations.

    :param detections:  numpy array with the detected events [float, seconds]
    :param annotations: numpy array with the annotated events [float, seconds]
    :param matches:     numpy array with indices of the closest events [int]
    :returns:           numpy array with the absolute errors [seconds]

    Note: The sequences must be ordered! To speed up the calculation, a list
          of pre-computed indices of the closest matches can be used.

    """
    # return the errors
    return np.abs(calc_errors(detections, annotations, matches))


def calc_relative_errors(detections, annotations, matches=None):
    """
    Relative errors of the detections to the closest annotations.

    :param detections:  numpy array with the detected events [float, seconds]
    :param annotations: numpy array with the annotated events [float, seconds]
    :param matches:     numpy array with indices of the closest events [int]
    :returns:           numpy array with the relative errors [seconds]

    Note: The sequences must be ordered! To speed up the calculation, a list of
          pre-computed indices of the closest matches can be used.

    """
    # if no detections or annotations are given
    if len(detections) == 0 or len(annotations) == 0:
        # return a empty array
        return np.zeros(0, dtype=np.float)
    # determine the closest annotations
    if matches is None:
        matches = find_closest_matches(detections, annotations)
    # calculate the absolute errors
    errors = calc_errors(detections, annotations, matches)
    # return the relative errors
    return np.abs(1 - (errors / annotations[matches]))


# evaluation classes
class SimpleEvaluation(object):
    """
    Simple evaluation class for calculating Precision, Recall and F-measure
    based on the numbers of true/false positive/negative detections.

    Note: so far, this class is only suitable for a 1-class evaluation problem.

    """
    def __init__(self, num_tp=0, num_fp=0, num_tn=0, num_fn=0):
        """
        Creates a new SimpleEvaluation object instance.

        :param num_tp: number of true positive detections
        :param num_fp: number of false positive detections
        :param num_tn: number of true negative detections
        :param num_fn: number of false negative detections

        """
        # hidden variables, to be able to overwrite them in subclasses
        self._num_tp = int(num_tp)
        self._num_fp = int(num_fp)
        self._num_tn = int(num_tn)
        self._num_fn = int(num_fn)
        # define the errors as an (empty) array here
        # subclasses are required to redefine as needed
        self._errors = np.zeros(0, dtype=np.float)

    # for adding another SimpleEvaluation object, i.e. summing them
    def __iadd__(self, other):
        if isinstance(other, SimpleEvaluation):
            # increase the counters
            self._num_tp += other.num_tp
            self._num_fp += other.num_fp
            self._num_tn += other.num_tn
            self._num_fn += other.num_fn
            # extend the errors array
            self._errors = np.append(self._errors, other.errors)
            # return the modified object
            return self
        else:
            raise TypeError('Can only add SimpleEvaluation or derived class to'
                            ' %s, not %s' % (type(self).__name__,
                                             type(other).__name__))

    # for adding two SimpleEvaluation objects
    def __add__(self, other):
        if isinstance(other, SimpleEvaluation):
            num_tp = self._num_tp + other.num_tp
            num_fp = self._num_fp + other.num_fp
            num_tn = self._num_tn + other.num_tn
            num_fn = self._num_fn + other.num_fn
            # create a new object
            new = SimpleEvaluation(num_tp, num_fp, num_tn, num_fn)
            # modify the hidden _errors variable directly
            new._errors = np.append(self._errors, other.errors)
            # return the newly created object
            return new
        else:
            raise TypeError('Can only add SimpleEvaluation or derived class to'
                            ' %s, not %s' % (type(self).__name__,
                                             type(other).__name__))

    @property
    def num_tp(self):
        """Number of true positive detections."""
        return self._num_tp

    @property
    def num_fp(self):
        """Number of false positive detections."""
        return self._num_fp

    @property
    def num_tn(self):
        """Number of true negative detections."""
        return self._num_tn

    @property
    def num_fn(self):
        """Number of false negative detections."""
        return self._num_fn

    @property
    def precision(self):
        """Precision."""
        # correct / retrieved
        retrieved = float(self.num_tp + self.num_fp)
        # if there are no positive predictions, none of them are wrong
        if retrieved == 0:
            return 1.
        return self.num_tp / retrieved

    @property
    def recall(self):
        """Recall."""
        # correct / relevant
        relevant = float(self.num_tp + self.num_fn)
        # if there are no positive annotations, we recalled all of them
        if relevant == 0:
            return 1.
        return self.num_tp / relevant

    @property
    def fmeasure(self):
        """F-measure."""
        # 2pr / (p+r)
        numerator = 2. * self.precision * self.recall
        if numerator == 0:
            return 0.
        return numerator / (self.precision + self.recall)

    @property
    def accuracy(self):
        """Accuracy."""
        # acc: (TP + TN) / (TP + FP + TN + FN)
        denominator = self.num_fp + self.num_fn + self.num_tp + self.num_tn
        if denominator == 0:
            return 1.
        numerator = float(self.num_tp + self.num_tn)
        if numerator == 0:
            return 0.
        return numerator / denominator

    @property
    def errors(self):
        """
        Errors of the true positive detections relative to the corresponding
        annotations.

        """
        # if any errors are given, they have to be the same length as the true
        # positive detections
        # Note: access the hidden variable _errors and the property num_tp
        #       because different classes implement the latter differently
        if len(self._errors) > 0 and len(self._errors) != self.num_tp:
            raise AssertionError("length of the errors and number of true "
                                 "positive detections must match")
        return self._errors

    @property
    def mean_error(self):
        """Mean of the errors."""
        if len(self.errors) == 0:
            return 0.
        return np.mean(self.errors)

    @property
    def std_error(self):
        """Standard deviation of the errors."""
        if len(self.errors) == 0:
            return 0.
        return np.std(self.errors)

    def print_errors(self, indent='', tex=False):
        """
        Print errors.

        :param indent: use the given string as indentation
        :param tex:    output format to be used in .tex files

        """
        # print the errors
        annotations = self.num_tp + self.num_fn
        tpr = self.recall
        fpr = (1 - self.precision)
        if tex:
            # tex formatting
            ret = 'tex & Precision & Recall & F-measure & True Positives & ' \
                  'False Positives & Accuracy & Mean & Std.dev\\\\\n %i ' \
                  'annotations & %.3f & %.3f & %.3f & %.3f & %.3f & %.3f & ' \
                  '%.2f ms & %.2f ms\\\\' % \
                  (annotations, self.precision, self.recall, self.fmeasure,
                   tpr, fpr, self.accuracy, self.mean_error * 1000.,
                   self.std_error * 1000.)
        else:
            # normal formatting
            ret = '%sannotations: %5d correct: %5d fp: %4d fn: %4d p=%.3f ' \
                  'r=%.3f f=%.3f\n%stpr: %.1f%% fpr: %.1f%% acc: %.1f%% ' \
                  'mean: %.1f ms std: %.1f ms' % \
                  (indent, annotations, self.num_tp, self.num_fp, self.num_fn,
                   self.precision, self.recall, self.fmeasure, indent,
                   tpr * 100., fpr * 100., self.accuracy * 100.,
                   self.mean_error * 1000., self.std_error * 1000.)
        # return
        return ret

    def __str__(self):
        return self.print_errors()


# class for summing Evaluations
SumEvaluation = SimpleEvaluation


# class for averaging Evaluations
class MeanEvaluation(SimpleEvaluation):
    """
    Simple evaluation class for averaging Precision, Recall and F-measure.

    """
    def __init__(self):
        """
        Creates a new MeanEvaluation object instance.

        """
        super(MeanEvaluation, self).__init__()
        # redefine most of the stuff as arrays so we can average them
        self._num_tp = np.zeros(0)
        self._num_fp = np.zeros(0)
        self._num_tn = np.zeros(0)
        self._num_fn = np.zeros(0)
        self._precision = np.zeros(0)
        self._recall = np.zeros(0)
        self._fmeasure = np.zeros(0)
        self._accuracy = np.zeros(0)
        self._errors = np.zeros(0)
        self._mean = np.zeros(0)
        self._std = np.zeros(0)

    # for adding another Evaluation object
    def append(self, other):
        """
        Appends the scores of another SimpleEvaluation (or derived class)
        object to the respective arrays.

        :param other: SimpleEvaluation (or derived class) object

        """
        if isinstance(other, SimpleEvaluation):
            # append the numbers of any Evaluation object to the arrays
            self._num_tp = np.append(self._num_tp, other.num_tp)
            self._num_fp = np.append(self._num_fp, other.num_fp)
            self._num_tn = np.append(self._num_tn, other.num_tn)
            self._num_fn = np.append(self._num_fn, other.num_fn)
            self._precision = np.append(self._precision, other.precision)
            self._recall = np.append(self._recall, other.recall)
            self._fmeasure = np.append(self._fmeasure, other.fmeasure)
            self._accuracy = np.append(self._accuracy, other.accuracy)
            self._errors = np.append(self._errors, other.errors)
            self._mean = np.append(self._mean, other.mean_error)
            self._std = np.append(self._std, other.std_error)
        else:
            raise TypeError('Can only append SimpleEvaluation or derived class'
                            ' to %s, not %s' % (type(self).__name__,
                                                type(other).__name__))

    @property
    def num_tp(self):
        """Number of true positive detections."""
        if len(self._num_tp) == 0:
            return 0.
        return np.mean(self._num_tp)

    @property
    def num_fp(self):
        """Number of false positive detections."""
        if len(self._num_fp) == 0:
            return 0.
        return np.mean(self._num_fp)

    @property
    def num_tn(self):
        """Number of true negative detections."""
        if len(self._num_tn) == 0:
            return 0.
        return np.mean(self._num_tn)

    @property
    def num_fn(self):
        """Number of false negative detections."""
        if len(self._num_fn) == 0:
            return 0.
        return np.mean(self._num_fn)

    @property
    def precision(self):
        """Precision."""
        if len(self._precision) == 0:
            return 0.
        return np.mean(self._precision)

    @property
    def recall(self):
        """Recall."""
        if len(self._recall) == 0:
            return 0.
        return np.mean(self._recall)

    @property
    def fmeasure(self):
        """F-measure."""
        if len(self._fmeasure) == 0:
            return 0.
        return np.mean(self._fmeasure)

    @property
    def accuracy(self):
        """Accuracy."""
        if len(self._accuracy) == 0:
            return 0.
        return np.mean(self._accuracy)

    @property
    def mean_error(self):
        """Mean of the errors."""
        if len(self._mean) == 0:
            return 0.
        return np.mean(self._mean)

    @property
    def std_error(self):
        """Standard deviation of the errors."""
        if len(self._std) == 0:
            return 0.
        return np.mean(self._std)


# class for evaluation of Precision, Recall, F-measure with arrays
class Evaluation(SimpleEvaluation):
    """
    Evaluation class for measuring Precision, Recall and F-measure based on
    numpy arrays with true/false positive/negative detections.

    """

    def __init__(self, tp=np.empty(0), fp=np.empty(0),
                 tn=np.empty(0), fn=np.empty(0)):
        """
        Creates a new Evaluation object instance.

        :param tp: numpy array with true positive detections [seconds]
        :param fp: numpy array with false positive detections [seconds]
        :param tn: numpy array with true negative detections [seconds]
        :param fn: numpy array with false negative detections [seconds]

        """
        super(Evaluation, self).__init__()
        self._tp = np.asarray(tp, dtype=np.float)
        self._fp = np.asarray(fp, dtype=np.float)
        self._tn = np.asarray(tn, dtype=np.float)
        self._fn = np.asarray(fn, dtype=np.float)

    # for adding another Evaluation object, i.e. summing them
    def __iadd__(self, other):
        if isinstance(other, Evaluation):
            # extend the arrays
            self._tp = np.append(self.tp, other.tp)
            self._fp = np.append(self.fp, other.fp)
            self._tn = np.append(self.tn, other.tn)
            self._fn = np.append(self.fn, other.fn)
            self._errors = np.append(self._errors, other.errors)
            # return the modified object
            return self
        else:
            raise TypeError('Can only add Evaluation or derived class to %s, '
                            'not %s' % (type(self).__name__,
                                        type(other).__name__))

    # for adding two Evaluation objects
    def __add__(self, other):
        if isinstance(other, Evaluation):
            # extend the arrays
            tp = np.append(self.tp, other.tp)
            fp = np.append(self.fp, other.fp)
            tn = np.append(self.tn, other.tn)
            fn = np.append(self.fn, other.fn)
            # create a new object
            new = Evaluation(tp, fp, tn, fn)
            # modify the hidden _errors variable directly
            new._errors = np.append(self._errors, other.errors)
            # return the newly created object
            return new
        else:
            raise TypeError('Can only add Evaluation or derived class to %s, '
                            'not %s' % (type(self).__name__,
                                        type(other).__name__))

    @property
    def tp(self):
        """True positive detections."""
        return self._tp

    @property
    def num_tp(self):
        """Number of true positive detections."""
        return len(self._tp)

    @property
    def fp(self):
        """False positive detections."""
        return self._fp

    @property
    def num_fp(self):
        """Number of false positive detections."""
        return len(self._fp)

    @property
    def tn(self):
        """True negative detections."""
        return self._tn

    @property
    def num_tn(self):
        """Number of true negative detections."""
        return len(self._tn)

    @property
    def fn(self):
        """False negative detections."""
        return self._fn

    @property
    def num_fn(self):
        """Number of false negative detections."""
        return len(self._fn)
