#!/usr/bin/env python
# encoding: utf-8
"""
This file contains all onset detection related functionality.

@author: Sebastian Böck <sebastian.boeck@jku.at>

"""

import os
import glob
import numpy as np
from scipy.ndimage.filters import uniform_filter, maximum_filter

from . import EventDetection, RnnEventDetection

EPSILON = 1e-6


# helper functions
def wrap_to_pi(phase):
    """
    Wrap the phase information to the range -π...π.

    :param phase: phase spectrogram
    :returns:     wrapped phase spectrogram

    """
    return np.mod(phase + np.pi, 2.0 * np.pi) - np.pi


def diff(spec, diff_frames=1, pos=False):
    """
    Calculates the difference of the magnitude spectrogram.

    :param spec:        the magnitude spectrogram
    :param diff_frames: calculate the difference to the N-th previous frame
    :param pos:         keep only positive values
    :returns:           (positive) magnitude spectrogram differences

    """
    # init the matrix with 0s, the first N rows are 0 then
    # TODO: under some circumstances it might be helpful to init with the spec
    # or use the frame at "real" index -N to calculate the diff to
    diff_spec = np.zeros_like(spec)
    if diff_frames < 1:
        raise ValueError("number of diff_frames must be >= 1")
    # calculate the diff
    diff_spec[diff_frames:] = spec[diff_frames:] - spec[:-diff_frames]
    # keep only positive values
    if pos:
        np.maximum(diff_spec, 0, diff_spec)
    return diff_spec


def correlation_diff(spec, diff_frames=1, pos=False, diff_bins=1):
    """
    Calculates the difference of the magnitude spectrogram relative to the
    N-th previous frame shifted in frequency to achieve the highest
    correlation between these two frames.

    :param spec:        the magnitude spectrogram
    :param diff_frames: calculate the difference to the N-th previous frame
    :param pos:         keep only positive values
    :param diff_bins:   maximum number of bins shifted for correlation
                        calculation
    :returns:           (positive) magnitude spectrogram differences

    """
    # init diff matrix
    diff_spec = np.zeros_like(spec)
    if diff_frames < 1:
        raise ValueError("number of diff_frames must be >= 1")
    # calculate the diff
    frames, bins = diff_spec.shape
    corr = np.zeros((frames, diff_bins * 2 + 1))
    for f in range(diff_frames, frames):
        # correlate the frame with the previous one
        # resulting size = bins * 2 - 1
        c = np.correlate(spec[f], spec[f - diff_frames], mode='full')
        # save the middle part
        centre = len(c) / 2
        corr[f] = c[centre - diff_bins: centre + diff_bins + 1]
        # shift the frame for difference calculation according to the
        # highest peak in correlation
        bin_offset = diff_bins - np.argmax(corr[f])
        bin_start = diff_bins + bin_offset
        bin_stop = bins - 2 * diff_bins + bin_start
        diff_spec[f, diff_bins:-diff_bins] = spec[f, diff_bins:-diff_bins] - \
            spec[f - diff_frames, bin_start:bin_stop]
    # keep only positive values
    if pos:
        np.maximum(diff_spec, 0, diff_spec)
    return diff_spec


# Onset Detection Functions
def high_frequency_content(spec):
    """
    High Frequency Content.

    :param spec: the magnitude spectrogram
    :returns:    high frequency content onset detection function

    "Computer Modeling of Sound for Transformation and Synthesis of Musical
     Signals"
    Paul Masri
    PhD thesis, University of Bristol, 1996

    """
    # HFC weights the magnitude spectrogram by the bin number,
    # thus emphasizing high frequencies
    return np.mean(spec * np.arange(spec.shape[1]), axis=1)


def spectral_diff(spec, diff_frames=1):
    """
    Spectral Diff.

    :param spec:        the magnitude spectrogram
    :param diff_frames: calculate the difference to the N-th previous frame
    :returns:           spectral diff onset detection function

    "A hybrid approach to musical note onset detection"
    Chris Duxbury, Mark Sandler and Matthew Davis
    Proceedings of the 5th International Conference on Digital Audio Effects
    (DAFx-02), 2002.

    """
    # Spectral diff is the sum of all squared positive 1st order differences
    return np.sum(diff(spec, diff_frames=diff_frames, pos=True) ** 2, axis=1)


def spectral_flux(spec, diff_frames=1):
    """
    Spectral Flux.

    :param spec:        the magnitude spectrogram
    :param diff_frames: calculate the difference to the N-th previous frame
    :returns:           spectral flux onset detection function

    "Computer Modeling of Sound for Transformation and Synthesis of Musical
     Signals"
    Paul Masri
    PhD thesis, University of Bristol, 1996

    """
    # Spectral flux is the sum of all positive 1st order differences
    return np.sum(diff(spec, diff_frames=diff_frames, pos=True), axis=1)


def superflux(spec, diff_frames=1, max_bins=3):
    """
    SuperFlux with a maximum peak-tracking stage for difference calculation.

    Calculates the difference of bin k of the magnitude spectrogram relative to
    the N-th previous frame with the maximum filtered spectrogram.

    :param spec:        the magnitude spectrogram
    :param diff_frames: calculate the difference to the N-th previous frame
    :param max_bins:    number of neighboring bins used for maximum filtering
    :returns:           SuperFlux onset detection function

    "Maximum Filter Vibrato Suppression for Onset Detection"
    Sebastian Böck and Gerhard Widmer
    Proceedings of the 16th International Conference on Digital Audio Effects
    (DAFx-13), 2013.

    Note: this method works only properly, if the spectrogram is filtered with
          a filterbank of the right frequency spacing. Filter banks with 24
          bands per octave (i.e. quarter-tone resolution) usually yield good
          results. With `max_bins=3`, the maximum of the bins k-1, k, k+1 of
          the frame `diff_frames` to the left is used for the calculation of
          the difference.

    """
    # init diff matrix
    diff_spec = np.zeros_like(spec)
    if diff_frames < 1:
        raise ValueError("number of diff_frames must be >= 1")
    # widen the spectrogram in frequency dimension by `max_bins`
    max_spec = maximum_filter(spec, size=[1, max_bins])
    # calculate the diff
    diff_spec[diff_frames:] = spec[diff_frames:] - max_spec[0:-diff_frames]
    # keep only positive values
    np.maximum(diff_spec, 0, diff_spec)
    # SuperFlux is the sum of all positive 1st order max. filtered differences
    return np.sum(diff_spec, axis=1)


def modified_kullback_leibler(spec, diff_frames=1, epsilon=EPSILON):
    """
    Modified Kullback-Leibler.

    :param spec:        the magnitude spectrogram
    :param diff_frames: calculate the difference to the N-th previous frame
    :param epsilon:     add epsilon to avoid division by 0
    :returns:           MKL onset detection function

    Note: the implementation presented in:
    "Automatic Annotation of Musical Audio for Interactive Applications"
    Paul Brossier
    PhD thesis, Queen Mary University of London, 2006

    is used instead of the original work:
    "Onset Detection in Musical Audio Signals"
    Stephen Hainsworth and Malcolm Macleod
    Proceedings of the International Computer Music Conference (ICMC), 2003

    """
    if epsilon <= 0:
        raise ValueError("a positive value must be added before division")
    mkl = np.zeros_like(spec)
    mkl[diff_frames:] = spec[diff_frames:] / (spec[:-diff_frames] + epsilon)
    # note: the original MKL uses sum instead of mean,
    # but the range of mean is much more suitable
    return np.mean(np.log(1 + mkl), axis=1)


def _phase_deviation(phase):
    """
    Helper method used by phase_deviation() & weighted_phase_deviation().

    :param phase: the phase spectrogram
    :returns:     phase deviation

    """
    pd = np.zeros_like(phase)
    # instantaneous frequency is given by the first difference
    # ψ′(n, k) = ψ(n, k) − ψ(n − 1, k)
    # change in instantaneous frequency is given by the second order difference
    # ψ′′(n, k) = ψ′(n, k) − ψ′(n − 1, k)
    pd[2:] = phase[2:] - 2 * phase[1:-1] + phase[:-2]
    # map to the range -pi..pi
    return wrap_to_pi(pd)


def phase_deviation(phase):
    """
    Phase Deviation.

    :param phase: the phase spectrogram
    :returns:     phase deviation onset detection function

    "On the use of phase and energy for musical onset detection in the complex
     domain"
    Juan Pablo Bello, Chris Duxbury, Matthew Davies and Mark Sandler
    IEEE Signal Processing Letters, Volume 11, Number 6, 2004

    """
    # take the mean of the absolute changes in instantaneous frequency
    return np.mean(np.abs(_phase_deviation(phase)), axis=1)


def weighted_phase_deviation(spec, phase):
    """
    Weighted Phase Deviation.

    :param spec:  the magnitude spectrogram
    :param phase: the phase spectrogram
    :returns:     weighted phase deviation onset detection function

    "Onset Detection Revisited"
    Simon Dixon
    Proceedings of the 9th International Conference on Digital Audio Effects
    (DAFx), 2006

    """
    # make sure the spectrogram is not filtered before
    if np.shape(phase) != np.shape(spec):
        raise ValueError("Magn. spectrogram and phase must be of same shape")
    # weighted_phase_deviation = spec * phase_deviation
    return np.mean(np.abs(_phase_deviation(phase) * spec), axis=1)


def normalized_weighted_phase_deviation(spec, phase, epsilon=EPSILON):
    """
    Normalized Weighted Phase Deviation.

    :param spec:    the magnitude spectrogram
    :param phase:   the phase spectrogram
    :param epsilon: add epsilon to avoid division by 0
    :returns:       normalized weighted phase deviation onset detection
                    function

    "Onset Detection Revisited"
    Simon Dixon
    Proceedings of the 9th International Conference on Digital Audio Effects
    (DAFx), 2006

    """
    if epsilon <= 0:
        raise ValueError("a positive value must be added before division")
    # normalize WPD by the sum of the spectrogram
    # (add a small epsilon so that we don't divide by 0)
    norm = np.add(np.mean(spec, axis=1), epsilon)
    return weighted_phase_deviation(spec, phase) / norm


def _complex_domain(spec, phase):
    """
    Helper method used by complex_domain() & rectified_complex_domain().

    :param spec:  the magnitude spectrogram
    :param phase: the phase spectrogram
    :returns:     complex domain

    Note: we use the simple implementation presented in:
    "Onset Detection Revisited"
    Simon Dixon
    Proceedings of the 9th International Conference on Digital Audio Effects
    (DAFx), 2006

    """
    if np.shape(phase) != np.shape(spec):
        raise ValueError("Magn. spectrogram and phase must be of same shape")
    # expected spectrogram
    cd_target = np.zeros_like(phase)
    # assume constant phase change
    cd_target[1:] = 2 * phase[1:] - phase[:-1]
    # add magnitude
    cd_target = spec * np.exp(1j * cd_target)
    # create complex spectrogram
    cd = spec * np.exp(1j * phase)
    # subtract the target values
    cd[1:] -= cd_target[:-1]
    return cd


def complex_domain(spec, phase):
    """
    Complex Domain.

    :param spec:  the magnitude spectrogram
    :param phase: the phase spectrogram
    :returns:     complex domain onset detection function

    "On the use of phase and energy for musical onset detection in the complex
     domain"
    Juan Pablo Bello, Chris Duxbury, Matthew Davies and Mark Sandler
    IEEE Signal Processing Letters, Volume 11, Number 6, 2004

    """
    # take the sum of the absolute changes
    return np.sum(np.abs(_complex_domain(spec, phase)), axis=1)


def rectified_complex_domain(spec, phase):
    """
    Rectified Complex Domain.

    :param spec:  the magnitude spectrogram
    :param phase: the phase spectrogram
    :returns:     rectified complex domain onset detection function

    "Onset Detection Revisited"
    Simon Dixon
    Proceedings of the 9th International Conference on Digital Audio Effects
    (DAFx), 2006

    """
    # rectified complex domain
    rcd = _complex_domain(spec, phase)
    # only keep values where the magnitude rises
    rcd *= diff(spec, pos=True)
    # take the sum of the absolute changes
    return np.sum(np.abs(rcd), axis=1)


# SpectralOnsetDetection default values
MAX_BINS = 3


class SpectralOnsetDetection(object):
    """
    The SpectralOnsetDetection class implements most of the common onset
    detection functions based on the magnitude or phase information of a
    spectrogram.

    """
    def __init__(self, spectrogram, max_bins=MAX_BINS, *args, **kwargs):
        """
        Creates a new SpectralOnsetDetection instance.

        :param spectrogram: the spectrogram object on which the detections
                            functions operate
        :param max_bins:    number of bins for the maximum filter
                            (for SuperFlux) [default=3]

        """
        # import
        from ..audio.spectrogram import Spectrogram
        # check spectrogram type
        if isinstance(spectrogram, Spectrogram):
            # already the right format
            self.spectrogram = spectrogram
        else:
            # assume a file name, try to instantiate a Spectrogram object
            self.spectrogram = Spectrogram(spectrogram, *args, **kwargs)
        self.max_bins = max_bins

    # FIXME: do use s.spec and s.diff directly instead of passing the number of
    # diff_frames to all these functions?

    # Onset Detection Functions
    def hfc(self):
        """High Frequency Content."""
        return high_frequency_content(self.spectrogram.spec)

    def sd(self):
        """Spectral Diff."""
        return spectral_diff(self.spectrogram.spec,
                             self.spectrogram.num_diff_frames)

    def sf(self):
        """Spectral Flux."""
        return spectral_flux(self.spectrogram.spec,
                             self.spectrogram.num_diff_frames)

    def superflux(self):
        """SuperFlux."""
        return superflux(self.spectrogram.spec,
                         self.spectrogram.num_diff_frames, self.max_bins)

    def mkl(self):
        """Modified Kullback-Leibler."""
        return modified_kullback_leibler(self.spectrogram.spec,
                                         self.spectrogram.num_diff_frames)

    def pd(self):
        """Phase Deviation."""
        return phase_deviation(self.spectrogram.phase)

    def wpd(self):
        """Weighted Phase Deviation."""
        return weighted_phase_deviation(self.spectrogram.spec,
                                        self.spectrogram.phase)

    def nwpd(self):
        """Normalized Weighted Phase Deviation."""
        return normalized_weighted_phase_deviation(self.spectrogram.spec,
                                                   self.spectrogram.phase)

    def cd(self):
        """Complex Domain."""
        return complex_domain(self.spectrogram.spec, self.spectrogram.phase)

    def rcd(self):
        """Rectified Complex Domain."""
        return rectified_complex_domain(self.spectrogram.spec,
                                        self.spectrogram.phase)

    @classmethod
    def add_arguments(cls, parser, method='superflux', methods=None,
                      max_bins=MAX_BINS):
        """
        Add spectral ODF related arguments to an existing parser object.

        :param parser:   existing argparse parser object
        :param method:   default ODF method
        :param methods:  list of ODF methods
        :param max_bins: number of bins for the maximum filter (for SuperFlux)
        :return:         spectral onset detection argument parser group object

        """
        # add spec related options to the existing parser
        # spectrogram options
        g = parser.add_argument_group('spectral onset detection arguments')
        superflux = False
        if methods is not None:
            g.add_argument('-o', dest='odf', default=method,
                        help='use one of these onset detection functions (%s) '
                                '[default=%s]' % (methods, method))
            if 'superflux' in methods:
                superflux = True
        # add SuperFlux arguments
        if superflux or method == 'superflux':
            g.add_argument('--max_bins', action='store', type=int,
                        default=max_bins,
                        help='bins used for maximum filtering [default='
                                '%(default)i]')
        # return the argument group so it can be modified if needed
        return g

# universal peak-picking method
def peak_picking(activations, threshold, smooth=None, pre_avg=0, post_avg=0,
                 pre_max=1, post_max=1):
    """
    Perform thresholding and peak-picking on the given activation function.

    :param activations: the onset activation function
    :param threshold:   threshold for peak-picking
    :param smooth:      smooth the activation function with the kernel
    :param pre_avg:     use N frames past information for moving average
    :param post_avg:    use N frames future information for moving average
    :param pre_max:     use N frames past information for moving maximum
    :param post_max:    use N frames future information for moving maximum

    Notes: If no moving average is needed (e.g. the activations are independent
           of the signal's level as for neural network activations), set
           `pre_avg` and `post_avg` to 0.

           For offline peak picking, set `pre_max` and `post_max` to 1.

           For online peak picking, set all `post_` parameters to 0.

    """
    # smooth activations
    kernel = None
    if isinstance(smooth, int):
        # size for the smoothing kernel is given
        if smooth > 1:
            kernel = np.hamming(smooth)
    elif isinstance(smooth, np.ndarray):
        # otherwise use the given smooth kernel directly
        if smooth.size > 1:
            kernel = smooth
    if kernel is not None:
        # convolve with the kernel
        activations = np.convolve(activations, kernel, 'same')
    # threshold activations
    avg_length = pre_avg + post_avg + 1
    if avg_length > 1:
        # compute a moving average
        avg_origin = int(np.floor((pre_avg - post_avg) / 2))
        # TODO: make the averaging function exchangeable (mean/median/etc.)
        mov_avg = uniform_filter(activations, avg_length, mode='constant',
                                 origin=avg_origin)
    else:
        # do not use a moving average
        mov_avg = 0
    # detections are those activations above the moving average + the threshold
    detections = activations * (activations >= mov_avg + threshold)
    # peak-picking
    max_length = pre_max + post_max + 1
    if max_length > 1:
        # compute a moving maximum
        max_origin = int(np.floor((pre_max - post_max) / 2))
        mov_max = maximum_filter(detections, max_length, mode='constant',
                                 origin=max_origin)
        # detections are peak positions
        detections *= (detections == mov_max)
    # return indices
    return np.nonzero(detections)[0]



class OnsetDetection(EventDetection):

    # default values for onset peak-picking
    ONLINE=False
    THRESHOLD = 1.25
    SMOOTH = 0
    PRE_AVG = 0.1
    POST_AVG = 0.03
    PRE_MAX = 0.03
    POST_MAX = 0.07
    # default values for onset reporting
    COMBINE = 0.03
    DELAY = 0

    def __init__(self, data, threshold=THRESHOLD, combine=COMBINE, delay=DELAY,
                 smooth=SMOOTH, pre_avg=PRE_AVG, post_avg=POST_MAX,
                 pre_max=PRE_MAX, post_max=POST_AVG, online=ONLINE, **kwargs):
        """
        Creates a new OnsetDetection instance.

        :param data:      Signal, activations or filename.
                          See EventDetection class for more details.
        :param threshold: threshold for peak-picking
        :param combine:   only report one onset within N seconds
        :param delay:     report onsets N seconds delayed
        :param smooth:    smooth the activation function over N seconds
        :param pre_avg:   use N seconds past information for moving average
        :param post_avg:  use N seconds future information for moving average
        :param pre_max:   use N seconds past information for moving maximum
        :param post_max:  use N seconds future information for moving maximum

        For more parameters see the parent classes.

        Notes: If no moving average is needed (e.g. the activations are
               independent of the signal's level as for neural network
               activations), `pre_avg` and `post_avg` should be set to 0.

               For offline peak picking set `pre_max` >= 1/fps and
               `post_max` >= 1/fps

               For online peak picking, all `post_` parameters are set to 0.

        """
        super(OnsetDetection, self).__init__(data, **kwargs)

        self.online = online
        self.threshold = threshold
        self.combine = combine
        self.delay = delay

        # convert timing information to frames and set default values
        # TODO: use at least 1 frame if any of these values are > 0?
        self.smooth = int(round(self.fps * smooth))
        self.pre_avg = int(round(self.fps * pre_avg))
        self.post_avg = int(round(self.fps * post_avg))
        self.pre_max = int(round(self.fps * pre_max))
        self.post_max = int(round(self.fps * post_max))
        # adjust some params for online mode
        if self.online:
            self.smooth = 0
            self.post_avg = 0
            self.post_max = 0

    def detect(self):
        """ See EventDetection class """
        # detect onsets (function returns int indices)
        detections = peak_picking(self.activations, self.threshold,
                                  self.smooth, self.pre_avg, self.post_avg,
                                  self.pre_max, self.post_max)

        # convert detected onsets to a list of timestamps
        detections = detections.astype(np.float) / self.fps
        # shift if necessary
        if self.delay != 0:
            detections += self.delay
        # always use the first detection and all others if none was reported
        # within the last `combine` seconds
        if detections.size > 1:
            # filter all detections which occur within `combine` seconds
            combined_detections = detections[1:][np.diff(detections) >
                                                 self.combine]
            # add them after the first detection
            detections = np.append(detections[0], combined_detections)
        else:
            detections = detections

        # also return the detections
        return detections

    @classmethod
    def add_arguments(cls, parser, threshold=THRESHOLD, smooth=SMOOTH,
                      combine=COMBINE, delay=DELAY, pre_avg=PRE_AVG,
                      post_avg=POST_AVG, pre_max=PRE_MAX, post_max=POST_MAX,
                      **kwargs):
        """
        Add onset detection related arguments to an existing parser object.

        :param parser:    existing argparse parser object
        :param threshold: threshold for peak-picking
        :param smooth:    smooth the onset activations over N seconds
        :param combine:   only report one onset within N seconds
        :param delay:     report onsets N seconds delayed
        :param pre_avg:   use N seconds past information for moving average
        :param post_avg:  use N seconds future information for moving average
        :param pre_max:   use N seconds past information for moving maximum
        :param post_max:  use N seconds future information for moving maximum
        :return:          onset detection argument parser group object

        """
        super(OnsetDetection, cls).add_arguments(parser, **kwargs)

        # add onset detection related options to the existing parser
        g = parser.add_argument_group('onset detection arguments')
        g.add_argument('-t', dest='threshold', action='store', type=float,
                       default=threshold, help='detection threshold '
                       '[default=%(default).2f]')
        g.add_argument('--smooth', action='store', type=float, default=smooth,
                       help='smooth the onset activations over N seconds '
                       '[default=%(default).2f]')
        g.add_argument('--combine', action='store', type=float,
                       default=combine, help='combine onsets within N seconds '
                       '[default=%(default).2f]')
        g.add_argument('--pre_avg', action='store', type=float,
                       default=pre_avg, help='build average over N previous '
                       'seconds [default=%(default).2f]')
        g.add_argument('--post_avg', action='store', type=float,
                       default=post_avg, help='build average over N following '
                       'seconds [default=%(default).2f]')
        g.add_argument('--pre_max', action='store', type=float,
                       default=pre_max, help='search maximum over N previous '
                       'seconds [default=%(default).2f]')
        g.add_argument('--post_max', action='store', type=float,
                       default=post_max, help='search maximum over N '
                       'following seconds [default=%(default).2f]')
        g.add_argument('--delay', action='store', type=float, default=delay,
                       help='report the onsets N seconds delayed '
                       '[default=%(default)i]')
        # return the argument group so it can be modified if needed
        return g


class RnnOnsetDetector(OnsetDetection, RnnEventDetection):
    # set the path to saved neural networks and generate lists of NN files
    NN_PATH = '%s/../ml/data' % (os.path.dirname(__file__))
    NN_FILES = glob.glob("%s/onsets_brnn*npz" % NN_PATH)

    # TODO: this information should be included/extracted in/from the NN files
    FPS = 100
    BANDS_PER_OCTAVE = 6
    MUL = 5
    ADD = 1
    NORM_FILTERS = True

    ## TODO: these do not seem to be used in the original implementation
    FMIN = 27.5
    FMAX = 18000
    RATIO = 0.25

    ONLINE = False
    WINDOW_SIZES = [1024, 2048, 4096]
    THRESHOLD = 0.35
    COMBINE = 0.03
    SMOOTH = 0.07
    PRE_AVG = 0
    POST_AVG = 0
    PRE_MAX = 1. / FPS
    POST_MAX = 1. / FPS


    def __init__(self, data, nn_files=NN_FILES, fps=FPS,
                 bands_per_octave=BANDS_PER_OCTAVE, mul=MUL, add=ADD,
                 norm_filters=NORM_FILTERS, online=ONLINE,
                 window_sizes=WINDOW_SIZES, threshold=THRESHOLD,
                 combine=COMBINE, smooth=SMOOTH, pre_avg=PRE_AVG,
                 post_avg=POST_AVG, pre_max=PRE_MAX, post_max=POST_MAX,
                 **kwargs):
        """
        Use RNNs to compute the activation function and pick the onsets

        :param data:      Signal, activations or file. See EventDetection class
        :param nn_files:  list of files that define the RNN
        :param fps:       frames per second
        :param bands_per_octave: number of filter bands per octave
        :param mul:          multiplier for logarithmic spectra
        :param add:          shift for logarithmic spectra
        :param norm_filters: sets if the logarithmic filterbank shall be
                             normalised
        :param online:    sets if online processing is desired
        :param window_sizes: list of window sizes for spectrogram computation
        :param threshold: threshold for peak-picking
        :param combine:   only report one onset within N seconds
        :param smooth:    smooth the activation function over N seconds
        :param pre_avg:   use N seconds past information for moving average
        :param post_avg:  use N seconds future information for moving average
        :param pre_max:   use N seconds past information for moving maximum
        :param post_max:  use N seconds future information for moving maximum

        See parent classes for more parameters.

        Notes: If no moving average is needed (e.g. the activations are
               independent of the signal's level as for neural network
               activations), `pre_avg` and `post_avg` should be set to 0.

               For offline peak picking set `pre_max` >= 1/fps and
               `post_max` >= 1/fps

               For online peak picking, all `post_` parameters are set to 0.

        """

        spr = super(RnnOnsetDetector, self)
        spr.__init__(data, nn_files=nn_files, fps=fps,
                     bands_per_octave=bands_per_octave, mul=mul, add=add,
                     norm_filters=norm_filters, online=online,
                     window_sizes=window_sizes, threshold=threshold,
                     combine=combine, smooth=smooth, pre_avg=pre_avg,
                     post_avg=post_avg, pre_max=pre_max, post_max=post_max,
                     **kwargs)

    @classmethod
    def add_arguments(cls, parser, nn_files=NN_FILES, fps=FPS,
                      bands_per_octave=BANDS_PER_OCTAVE, mul=MUL, add=ADD,
                      norm_filters=NORM_FILTERS, online=ONLINE,
                      window_sizes=WINDOW_SIZES, threshold=THRESHOLD,
                      combine=COMBINE, smooth=SMOOTH, pre_avg=PRE_AVG,
                      post_avg=POST_AVG, pre_max=PRE_MAX, post_max=POST_MAX,
                      **kwargs):
        """
        Add RnnOnsetDetection options to an existing parser object.
        This method just sets standard values. For a detailed parameter
        description, see the parent classes.
        """

        spr = super(RnnOnsetDetector, cls)
        spr.add_arguments(parser, nn_files=nn_files, fps=fps,
                          bands_per_octave=bands_per_octave, mul=mul, add=add,
                          norm_filters=norm_filters, online=online,
                          window_sizes=window_sizes, threshold=threshold,
                          combine=combine, smooth=smooth, pre_avg=pre_avg,
                          post_avg=post_avg, pre_max=pre_max,
                          post_max=post_max, **kwargs)


def parser():
    """
    Command line argument parser for onset detection.

    """
    import argparse
    from ..utils.params import (audio, spec, filtering, log, spectral_odf,
                                onset, save_load)

    # define parser
    p = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, description="""
    If invoked without any parameters, the software detects all onsets in
    the given files according to the method proposed in:

    "Maximum Filter Vibrato Suppression for Onset Detection"
    by Sebastian Böck and Gerhard Widmer
    Proceedings of the 16th International Conference on Digital Audio Effects
    (DAFx-13), Maynooth, Ireland, September 2013

    """)
    # general options
    p.add_argument('files', metavar='files', nargs='+',
                   help='files to be processed')
    p.add_argument('-v', dest='verbose', action='store_true',
                   help='be verbose')
    p.add_argument('--ext', action='store', type=str, default='txt',
                   help='extension for detections [default=txt]')
    # add other argument groups
    audio(p, online=False)
    spec(p)
    filtering(p, default=True)
    log(p, default=True)
    spectral_odf(p)
    o = onset(p)
    # list of offered ODFs
    methods = ['superflux', 'hfc', 'sd', 'sf', 'mkl', 'pd', 'wpd', 'nwpd',
               'cd', 'rcd']
    o.add_argument('-o', dest='odf', default='superflux',
                   help='use this onset detection function %s' % methods)
    save_load(p)
    # parse arguments
    args = p.parse_args()
    # print arguments
    if args.verbose:
        print args
    # return args
    return args


def main():
    """
    Example onset detection program.

    """
    import os.path

    from ..utils import files
    from ..audio.wav import Wav
    from ..audio.spectrogram import Spectrogram
    from ..audio.filters import LogarithmicFilterbank

    # parse arguments
    args = parser()

    # TODO: also add an option for evaluation and load the targets accordingly
    # see cp.evaluation.helpers.match_files()

    # init filterbank
    fb = None

    # which files to process
    if args.load:
        # load the activations
        ext = '.activations'
    else:
        # only process .wav files
        ext = '.wav'
    # process the files
    for f in files(args.files, ext):
        if args.verbose:
            print f

        # use the name of the file without the extension
        filename = os.path.splitext(f)[0]

        # do the processing stuff unless the activations are loaded from file
        if args.load:
            # load the activations from file
            # FIXME: fps must be encoded in the file
            o = Onset(f, args.fps, args.online)
        else:
            # create a Wav object
            w = Wav(f, mono=True, norm=args.norm, att=args.att)
            if args.filter:
                # (re-)create filterbank if the sample rate is not the same
                if fb is None or fb.sample_rate != w.sample_rate:
                    # create filterbank if needed
                    fb = LogarithmicFilterbank(num_fft_bins=args.window / 2,
                                               sample_rate=w.sample_rate,
                                               bands_per_octave=args.bands,
                                               fmin=args.fmin, fmax=args.fmax,
                                               norm=args.equal)
            # create a Spectrogram object
            s = Spectrogram(w, frame_size=args.window, filterbank=fb,
                            log=args.log, mul=args.mul, add=args.add,
                            ratio=args.ratio, diff_frames=args.diff_frames)
            # create a SpectralOnsetDetection object
            sod = SpectralOnsetDetection(s, max_bins=args.max_bins)
            # perform detection function on the object
            act = getattr(sod, args.odf)()
            # create an Onset object with the activations
            o = Onset(act, args.fps, args.online)
        # save onset activations or detect onsets
        if args.save:
            # save the raw ODF activations
            o.save_activations("%s.%s" % (filename, args.odf))
        else:
            # detect the onsets
            o.detect(args.threshold, combine=args.combine, delay=args.delay,
                     smooth=args.smooth, pre_avg=args.pre_avg,
                     post_avg=args.post_avg, pre_max=args.pre_max,
                     post_max=args.post_max)
            # write the onsets to a file
            o.write("%s.%s" % (filename, args.ext))
            # also output them to stdout if verbose
            if args.verbose:
                print 'detections:', o.detections
        # continue with next file

if __name__ == '__main__':
    main()
