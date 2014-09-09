#!/usr/bin/env python
# encoding: utf-8
"""
This file contains spectrogram related functionality.

@author: Sebastian Böck <sebastian.boeck@jku.at>

"""

import numpy as np
import scipy.fftpack as fft

from .filters import fft_freqs, A4


def stft(x, window, hop_size, offset=0, phase=False, fft_size=None):
    """
    Calculates the Short-Time-Fourier-Transform of the given signal.

    :param x:        discrete signal (1D numpy array)
    :param window:   window function (1D numpy array)
    :param hop_size: the hop size in samples between adjacent frames [float]
    :param offset:   position of the first sample inside the signal [int]
    :param phase:    circular shift for correct phase [bool]
    :param fft_size: use given size for FFT [int, should be a power of 2]
    :return:         the complex STFT of the signal

    The size of the window determines the frame size used for splitting the
    signal into frames.

    """
    from .signal import signal_frame

    # if the signal is not scaled, scale the window function accordingly
    try:
        fft_window = window / np.iinfo(x.dtype).max
    except ValueError:
        fft_window = window
    # size of window
    window_size = window.size
    # number of samples
    samples = len(x)
    # number of frames
    frames = int(np.ceil(samples / float(hop_size)))
    # size of FFT
    if fft_size is None:
        fft_size = window_size
    # number of resulting FFT bins
    num_fft_bins = fft_size >> 1
    # init stft matrix
    y = np.zeros([frames, num_fft_bins], np.complex64)
    # perform STFT
    for frame in range(frames):
        # get the right portion of the signal
        fft_signal = signal_frame(x, frame, window_size, hop_size, offset)
        # multiply the signal with the window function
        fft_signal = np.multiply(fft_signal, fft_window)
        # only shift and perform complex DFT if needed
        if phase:
            # circular shift the signal (needed for correct phase)
            fft_signal = np.concatenate(fft_signal[window_size / 2:],
                                        fft_signal[:window_size / 2])
        # perform DFT
        y[frame] = fft.fft(fft_signal, fft_size)[:num_fft_bins]
        # next frame
    # return
    return y


def strided_stft(signal, window, hop_size, phase=True):
    """
    Calculates the Short-Time-Fourier-Transform of the given signal.

    :param signal:   the discrete signal
    :param window:   window function
    :param hop_size: the hop size in samples between adjacent frames [int]
    :param phase:    circular shift for correct phase [bool]
    :return:         the complex STFT of the signal

    Note: This function is here only for completeness. It is faster only in
          rare circumstances. Also, seeking to the right position is only
          working properly, if integer hop_sizes are used.

    """
    from .signal import strided_frames

    # init variables
    ffts = window.size >> 1
    # get a strided version of the signal
    fft_signal = strided_frames(signal, window.size, hop_size)
    # circular shift the signal
    if phase:
        fft_signal = fft.fftshift(fft_signal)
    # apply window function
    fft_signal *= window
    # perform the FFT
    return fft.fft(fft_signal)[:, :ffts]


def tuning_frequency(spec, sample_rate, num_hist_bins=15, fref=A4):
    """
    Determines the tuning frequency based on the given (peak) magnitude
    spectrogram.

    :param spec:          (peak) magnitude spectrogram [2D numpy array]
    :param sample_rate:   sample rate of the audio file [Hz]
    :param num_hist_bins: number of histogram bins
    :param fref:          reference tuning frequency [Hz]
    :return:              tuning frequency

    """
    # frequencies of the bins
    bin_freqs = fft_freqs(spec.shape[1], sample_rate)
    # interval of spectral bins from the reference frequency in semitones
    semitone_int = 12. * np.log2(bin_freqs / fref)
    # deviation from the next semitone
    semitone_dev = semitone_int - np.round(semitone_int)
    # build a histogram
    hist = np.histogram(semitone_dev * spec,
                        bins=num_hist_bins, range=(-0.5, 0.5))
    # deviation of the bins (calculate the bin centres)
    dev_bins = (hist[1][:-1] + hist[1][1:]) / 2.
    # dominant deviation
    dev = num_hist_bins * dev_bins[np.argmax(hist[0])]
    # calculate the tuning frequency
    return fref * 2. ** (dev / 12.)


# Spectrogram defaults
FILTERBANK = None
LOG = False  # default: linear spectrogram
MUL = 1
ADD = 1
NORM_WINDOW = False
FFT_SIZE = None
BLOCK_SIZE = 2048
RATIO = 0.5
DIFF_FRAMES = None


class Spectrogram(object):
    """
    Spectrogram Class.

    """
    def __init__(self, frames, window=np.hanning, filterbank=FILTERBANK,
                 log=LOG, mul=MUL, add=ADD, norm_window=NORM_WINDOW,
                 fft_size=FFT_SIZE, block_size=BLOCK_SIZE, ratio=RATIO,
                 diff_frames=DIFF_FRAMES, *args, **kwargs):
        """
        Creates a new Spectrogram instance of the given audio.

        :param frames: a FramedSignal object, or a file name or file handle
        :param window: window function

        Magnitude spectrogram manipulation parameters:

        :param filterbank: filterbank used for dimensionality reduction of the
                           magnitude spectrogram

        :param log: take the logarithm of the magnitude [bool]
        :param mul: multiplier before taking the logarithm of the magnitude
        :param add: add this value before taking the logarithm of the magnitude

        FFT parameters:

        :param norm_window: set area of window function to 1 [bool]
        :param fft_size:    use this size for FFT [int, should be a power of 2]
        :param block_size:  perform filtering in blocks of N frames
                            [int, should be a power of 2]; additionally `False`
                            can be used to switch off block wise processing

        Diff parameters:

        :param ratio:       calculate the difference to the frame which window
                            overlaps to this ratio [float]
        :param diff_frames: calculate the difference to the N-th previous frame
                            [int] (if set, this overrides the value calculated
                            from the ratio)

        :param args:        arguments passed to FramedSignal()
        :param kwargs:      keyword arguments passed to FramedSignal()

        Note: including phase and/or local group delay information slows down
              calculation considerably (phase: *2; lgd: *3)!

        """
        from .signal import FramedSignal
        # audio signal stuff
        if isinstance(frames, FramedSignal):
            # already a FramedSignal
            self._frames = frames
        else:
            # try to instantiate a FramedSignal object
            self._frames = FramedSignal(frames, *args, **kwargs)

        # determine window to use
        if hasattr(window, '__call__'):
            # if only function is given, use the size to the audio frame size
            self._window = window(self._frames.frame_size)
        elif isinstance(window, np.ndarray):
            # otherwise use the given window directly
            self._window = window
        else:
            # other types are not supported
            raise TypeError("Invalid window type.")
        # normalize the window if needed
        if norm_window:
            self._window /= np.sum(self._window)
        # window used for DFT
        try:
            # the audio signal is not scaled, scale the window accordingly
            max_value = np.iinfo(self.frames.signal.data.dtype).max
            self._fft_window = self.window / max_value
        except ValueError:
            self._fft_window = self.window

        # parameters used for the DFT
        if fft_size is None:
            self._fft_size = self.window.size
        else:
            self._fft_size = fft_size

        # perform some calculations (e.g. filtering) in blocks of that size
        self.block_size = block_size

        # init matrices
        self._spec = None
        self._stft = None
        self._phase = None
        self._lgd = None

        # parameters for magnitude spectrogram processing
        self._filterbank = filterbank
        self._log = log
        self._mul = mul
        self._add = add

        # TODO: does this attribute belong to this class?
        self._diff = None
        # diff parameters
        self._ratio = ratio
        if not diff_frames:
            # calculate on basis of the ratio
            # get the first sample with a higher magnitude than given ratio
            sample = np.argmax(self.window > self.ratio * max(self.window))
            diff_samples = self.window.size / 2 - sample
            # convert to frames
            diff_frames = int(round(diff_samples / self.frames.hop_size))
        # always set the minimum to 1
        if diff_frames < 1:
            diff_frames = 1
        self._diff_frames = diff_frames

        # other stuff
        self._ssd = None
        self._tuning_frequency = None

    @property
    def frames(self):
        """Audio frames."""
        return self._frames

    @property
    def num_frames(self):
        """Number of frames."""
        return len(self._frames)

    @property
    def window(self):
        """Window function."""
        return self._window

    @property
    def fft_size(self):
        """Size of the FFT."""
        return self._fft_size

    @property
    def fft_freqs(self):
        """Frequencies of the FFT bins."""
        return fft_freqs(self.num_fft_bins, self.frames.signal.sample_rate)

    @property
    def num_fft_bins(self):
        """Number of FFT bins."""
        return self._fft_size >> 1

    @property
    def filterbank(self):
        """Filterbank with which the spectrogram is filtered."""
        return self._filterbank

    @property
    def num_bins(self):
        """Number of bins of the spectrogram."""
        if self.filterbank is None:
            return self.num_fft_bins
        else:
            return self.filterbank.shape[1]

    @property
    def log(self):
        """Logarithmic magnitude."""
        return self._log

    @property
    def mul(self):
        """
        Multiply by this value before taking the logarithm of the magnitude.

        """
        return self._mul

    @property
    def add(self):
        """Add this value before taking the logarithm of the magnitude."""
        return self._add

    def compute_stft(self, stft=None, phase=None, lgd=None, block_size=None):
        """
        This is a memory saving method to batch-compute different spectrograms.

        :param stft:       save the raw complex STFT to the "stft" attribute
        :param phase:      save the phase of the STFT to the "phase" attribute
        :param lgd:        save the local group delay of the STFT to the "lgd"
                           attribute
        :param block_size: perform filtering in blocks of that size [frames]

        Note: bigger blocks lead to higher memory consumption but generally get
              computed faster than smaller blocks; too big block might decrease
              performance again.

        """
        # cache variables
        num_frames = self.num_frames
        num_fft_bins = self.num_fft_bins

        # init spectrogram matrix
        self._spec = np.zeros([num_frames, self.num_bins], np.float32)
        # STFT matrix
        if stft:
            self._stft = np.zeros([num_frames, num_fft_bins],
                                  dtype=np.complex64)
        # phase matrix
        if phase:
            self._phase = np.zeros([num_frames, num_fft_bins],
                                   dtype=np.float32)
        # local group delay matrix
        if lgd:
            self._lgd = np.zeros([num_frames, num_fft_bins], dtype=np.float32)

        # process in blocks
        if self._filterbank is not None:
            if block_size is None:
                block_size = self.block_size
            if not block_size or block_size > num_frames:
                block_size = num_frames
            # init a matrix of that size
            spec = np.zeros([block_size, self.num_fft_bins])

        # calculate DFT for all frames
        for f, frame in enumerate(self.frames):
            # multiply the signal frame with the window function
            signal = np.multiply(frame, self._fft_window)
            # only shift and perform complex DFT if needed
            if stft or phase or lgd:
                # circular shift the signal (needed for correct phase)
                signal = np.concatenate((signal[num_fft_bins:],
                                         signal[:num_fft_bins]))
            # perform DFT
            dft = fft.fft(signal, self.fft_size)[:num_fft_bins]

            # save raw stft
            if stft:
                self._stft[f] = dft
            # phase / lgd
            if phase or lgd:
                angle = np.angle(dft)
            # save phase
            if phase:
                self._phase[f] = angle
            # save lgd
            if lgd:
                # unwrap phase
                unwrapped_phase = np.unwrap(angle)
                # local group delay is the derivative over frequency
                self._lgd[f, :-1] = unwrapped_phase[:-1] - unwrapped_phase[1:]

            # is block wise processing needed?
            if self._filterbank is None:
                # no filtering needed, thus no block wise processing needed
                self._spec[f] = np.abs(dft)
            else:
                # filter the magnitude spectrogram in blocks
                spec[f % block_size] = np.abs(dft)
                # if the end of a block or end of the signal is reached
                end_of_block = (f + 1) % block_size == 0
                end_of_signal = (f + 1) == num_frames
                if end_of_block or end_of_signal:
                    start = f // block_size * block_size
                    self._spec[start:f + 1] = np.dot(spec[:f % block_size + 1],
                                                     self.filterbank)

        # take the logarithm if needed
        if self.log:
            self._spec = np.log10(self.mul * self._spec + self.add)

    @property
    def stft(self):
        """Short Time Fourier Transform of the signal."""
        # TODO: this is highly inefficient if other properties depending on the
        # STFT were accessed previously; better call compute_stft() with
        # appropriate parameters.
        if self._stft is None:
            self.compute_stft(stft=True)
        return self._stft

    @property
    def spec(self):
        """Magnitude spectrogram of the STFT."""
        # TODO: this is highly inefficient if more properties are accessed;
        # better call compute_stft() with appropriate parameters.
        if self._spec is None:
            # check if STFT was computed already
            if self._stft is not None:
                # use it
                self._spec = np.abs(self._stft)
                # filter if needed
                if self._filterbank is not None:
                    self._spec = np.dot(self._spec, self._filterbank)
                # take the logarithm
                if self._log:
                    self._spec = np.log10(self._mul * self._spec + self._add)
            else:
                # compute the spec
                self.compute_stft()
        # return spec
        return self._spec

    # alias
    magnitude = spec

    @property
    def ratio(self):
        # TODO: come up with a better description
        """Window overlap ratio."""
        return self._ratio

    @property
    def num_diff_frames(self):
        """
        Number of frames used for difference calculation of the magnitude
        spectrogram.

        """
        return self._diff_frames

    @property
    def diff(self):
        """Differences of the magnitude spectrogram."""
        if self._diff is None:
            # init array
            self._diff = np.zeros_like(self.spec)
            # calculate the diff
            df = self.num_diff_frames
            self._diff[df:] = self.spec[df:] - self.spec[:-df]
            # TODO: make the filling of the first diff_frames work properly
        # return diff
        return self._diff

    @property
    def pos_diff(self):
        """Positive differences of the magnitude spectrogram."""
        # return only the positive elements of the diff
        return np.maximum(self.diff, 0)

    @property
    def phase(self):
        """Phase of the STFT."""
        # TODO: this is highly inefficient if other properties depending on the
        # phase were accessed previously; better call compute_stft() with
        # appropriate parameters.
        if self._phase is None:
            # check if STFT was computed already
            if self._stft is not None:
                # use it
                self._phase = np.angle(self._stft)
            else:
                # compute the phase
                self.compute_stft(phase=True)
        # return phase
        return self._phase

    @property
    def lgd(self):
        """Local group delay of the STFT."""
        # TODO: this is highly inefficient if more properties are accessed;
        # better call compute_stft() with appropriate parameters.
        if self._lgd is None:
            # if the STFT was computed already, but not the phase
            if self._stft is not None and self._phase is None:
                # save the phase as well
                # FIXME: this uses unneeded memory, if only STFT and LGD are of
                # interest, but not the phase (very rare case only)
                self._phase = np.angle(self._stft)
            # check if phase was computed already
            if self._phase is not None:
                # FIXME: remove duplicate code
                # unwrap phase over frequency axis
                unwrapped = np.unwrap(self._phase, axis=1)
                # local group delay is the derivative over frequency
                self._lgd = np.zeros_like(self._phase)
                self._lgd[:, :-1] = unwrapped[:, :-1] - unwrapped[:, 1:]
            else:
                # compute the local group delay
                self.compute_stft(lgd=True)
        # return lgd
        return self._lgd

    def aw(self, floor=0.5, relaxation=10):
        """
        Return an adaptively whitened version of the magnitude spectrogram.

        :param floor:      floor coefficient [float]
        :param relaxation: relaxation time [frames]
        :return:           the whitened magnitude spectrogram

        "Adaptive Whitening For Improved Real-time Audio Onset Detection"
        Dan Stowell and Mark Plumbley
        Proceedings of the International Computer Music Conference (ICMC), 2007

        """
        relaxation = 10.0 ** (-6. * relaxation / self.frames.fps)
        p = np.zeros_like(self.spec)
        # iterate over all frames
        for f in range(len(self.frames)):
            if f > 0:
                p[f] = np.maximum(self.spec[f], floor, relaxation * p[f - 1])
            else:
                p[f] = np.maximum(self.spec[f], floor)
        # return the whitened spectrogram
        return self.spec / p

    @property
    def ssd(self):
        """
        Statistical Spectrum Descriptors of the STFT.

        "Evaluation of Feature Extractors and Psycho-acoustic Transformations
         for Music Genre Classification."
        T. Lidy and A. Rauber
        Proceedings of the 6th International Conference on Music Information
        Retrieval (ISMIR 2005), London, UK, September 2005

        """
        if self._ssd is None:
            from scipy.stats import skew, kurtosis
            self._ssd = {'mean': np.mean(self.spec, axis=0),
                         'median': np.median(self.spec, axis=0),
                         'variance': np.var(self.spec, axis=0),
                         'skewness': skew(self.spec, axis=0),
                         'kurtosis': kurtosis(self.spec, axis=0),
                         'min': np.min(self.spec, axis=0),
                         'max': np.max(self.spec, axis=0)}
        return self._ssd

    @property
    def tuning_frequency(self):
        """
        Determines the tuning frequency of the spectrogram.

        :return: tuning frequency

        """
        if self._tuning_frequency is None:
            # make sure the spec is in the right form to do the calculation
            if self.filterbank is None:
                spec = self.spec
            else:
                spec = np.abs(self.stft)
            # calculate the reference frequency
            fref = tuning_frequency(spec, self.frames.signal.sample_rate)
            self._tuning_frequency = fref
        return self._tuning_frequency

    def copy(self, window=None, filterbank=None, log=None, mul=None, add=None,
             norm_window=None, fft_size=None, block_size=None, ratio=None,
             diff_frames=None):
        """
        Copies the Spectrogram object and adjusts some parameters.

        :param window:      window function
        :param filterbank:  filterbank used for dimensionality reduction of the
                            magnitude spectrogram
        :param log:         take the logarithm of the magnitude [bool]
        :param mul:         multiplier before taking the logarithm
        :param add:         add this value before taking the logarithm
        :param norm_window: set area of window function to 1 [bool]
        :param fft_size:    use this size for FFT [int, should be a power of 2]
        :param block_size:  perform filtering in blocks of N frames
        :param ratio:       calculate the difference to the frame which window
                            overlaps to this ratio [float]
        :param diff_frames: calculate the difference to the N-th previous frame
                            [int] (if set, this overrides the value calculated
                            from the ratio)
        :return:            a new Spectrogram object

        """
        # copy the object attributes unless overwritten by passing other values
        if window is None:
            window = self.window
        if filterbank is None:
            filterbank = self.filterbank
        if log is None:
            log = self.log
        if mul is None:
            mul = self.mul
        if add is None:
            add = self.add
        if fft_size is None:
            fft_size = self.fft_size
        if block_size is None:
            block_size = self.block_size
        if ratio is None:
            ratio = self.ratio
        if diff_frames is None:
            diff_frames = self.num_diff_frames
        # return a new FramedSignal
        return Spectrogram(self.frames, window=window, filterbank=filterbank,
                           log=log, mul=mul, add=add, norm_window=norm_window,
                           fft_size=fft_size, block_size=block_size,
                           ratio=ratio, diff_frames=diff_frames)

    def __str__(self):
        txt = "Spectrogram: "
        if self.log:
            txt += "logarithmic magnitude; mul: %.2f; add: %.2f; " % (self.mul,
                                                                      self.add)
        if self.filterbank is not None:
            txt += "\n %s" % str(self.filterbank)
        return "%s\n %s" % (txt, str(self.frames))

    @staticmethod
    def add_arguments(parser, ratio=RATIO, diff_frames=DIFF_FRAMES, log=LOG,
                      mul=MUL, add=ADD):
        """
        Add spectrogram related arguments to an existing parser object.

        :param parser:      existing argparse parser object
        :param ratio:       calculate the difference to the frame which window
                            overlaps to this ratio
        :param diff_frames: calculate the difference to the N-th previous frame
        :param log:         include logarithm options (adds a switch to negate)
        :param mul:         multiply the magnitude spectrogram with given value
        :param add:         add the given value to the magnitude spectrogram
        :return:            spectrogram argument parser group object

        """
        # add spec related options to the existing parser
        g = parser.add_argument_group('spectrogram arguments')
        g.add_argument('--ratio', action='store', type=float, default=ratio,
                       help='window magnitude ratio to calc number of diff '
                       'frames [default=%(default).1f]')
        g.add_argument('--diff_frames', action='store', type=int,
                       default=diff_frames, help='number of diff frames '
                       '(if set, this overrides the value calculated from '
                       'the ratio)')
        # add log related options to the existing parser if needed
        l = None
        if log is not None:
            l = parser.add_argument_group('logarithmic magnitude arguments')
            if log:
                l.add_argument('--no_log', dest='log',
                               action='store_false', default=log,
                               help='no logarithmic magnitude '
                               '[default=logarithmic]')
            else:
                l.add_argument('--log', action='store_true',
                               default=-log, help='logarithmic '
                               'magnitude [default=linear]')
            if mul is not None:
                l.add_argument('--mul', action='store', type=float,
                               default=mul, help='multiplier (before taking '
                               ' the log) [default=%(default)i]')
            if add is not None:
                l.add_argument('--add', action='store', type=float,
                               default=add, help='value added (before taking '
                               'the log) [default=%(default)i]')
        # return the groups
        return g, l


class FilteredSpectrogram(Spectrogram):
    """
    FilteredSpectrogram is a subclass of Spectrogram which filters the
    magnitude spectrogram based on the given filterbank.

    """
    def __init__(self, *args, **kwargs):
        """
        Creates a new FilteredSpectrogram instance.

        :param filterbank: filterbank for dimensionality reduction

        If no filterbank is given, one with the following parameters is created
        automatically:

        :param bands_per_octave: number of filter bands per octave
        :param fmin:             the minimum frequency [Hz]
        :param fmax:             the maximum frequency [Hz]
        :param norm_filters:     normalize the filter to area 1 [bool]
        :param a4:               tuning frequency of A4 [Hz]

        """
        from .filters import (LogarithmicFilterbank, BANDS_PER_OCTAVE, FMIN,
                              FMAX, NORM_FILTERS, DUPLICATE_FILTERS)
        # fetch the arguments for filterbank creation (or set defaults)
        fb = kwargs.pop('filterbank', None)
        bands_per_octave = kwargs.pop('bands_per_octave', BANDS_PER_OCTAVE)
        fmin = kwargs.pop('fmin', FMIN)
        fmax = kwargs.pop('fmax', FMAX)
        norm_filters = kwargs.pop('norm_filters', NORM_FILTERS)
        duplicate_filters = kwargs.pop('duplicate_filters', DUPLICATE_FILTERS)
        # create Spectrogram object
        super(FilteredSpectrogram, self).__init__(*args, **kwargs)
        # if no filterbank was given, create one
        if fb is None:
            sample_rate = self.frames.signal.sample_rate
            fb = LogarithmicFilterbank(num_fft_bins=self.num_fft_bins,
                                       sample_rate=sample_rate,
                                       bands_per_octave=bands_per_octave,
                                       fmin=fmin, fmax=fmax, norm=norm_filters,
                                       duplicates=duplicate_filters)
        # save the filterbank, so it gets used for computation
        self._filterbank = fb

# aliases
FiltSpec = FilteredSpectrogram
FS = FiltSpec


class LogarithmicFilteredSpectrogram(FilteredSpectrogram):
    """
    LogarithmicFilteredSpectrogram is a subclass of FilteredSpectrogram which
    filters the magnitude spectrogram based on the given filterbank and
    converts it to a logarithmic (magnitude) scale.

    """
    def __init__(self, *args, **kwargs):
        """
        Creates a new LogarithmicFilteredSpectrogram instance.

        The magnitudes of the filtered spectrogram are then converted to a
        logarithmic scale.

        :param mul: multiply the magnitude spectrogram with given value
        :param add: add the given value to the magnitude spectrogram

        """
        # fetch the arguments for logarithmic magnitude (or set defaults)
        mul = kwargs.pop('mul', MUL)
        add = kwargs.pop('add', ADD)
        # create a Spectrogram object
        super(LogarithmicFilteredSpectrogram, self).__init__(*args, **kwargs)
        # set the parameters, so they get used for computation
        self._log = True
        self._mul = mul
        self._add = add

# aliases
LogFiltSpec = LogarithmicFilteredSpectrogram
LFS = LogFiltSpec


# harmonic/percussive separation stuff
# TODO: move this to an extra module?
MASKING = 'binary'
HARMONIC_FILTER = (15, 1)
PERCUSSIVE_FILTER = (1, 15)

from scipy.ndimage.filters import median_filter


class HarmonicPercussiveSourceSeparation(Spectrogram):
    """
    HarmonicPercussiveSourceSeparation is a subclass of Spectrogram and
    separates the magnitude spectrogram into its harmonic and percussive
    components with median filters.

    "Harmonic/percussive separation using median filtering."
    Derry FitzGerald.
    Proceedings of the 13th International Conference on Digital Audio Effects
    (DAFx-10), Graz, Austria, September 2010.

    """
    def __init__(self, *args, **kwargs):
        """
        Creates a new HarmonicPercussiveSourceSeparation instance.

        The magnitude spectrogram are separated with median filters with the
        given sizes into their harmonic and percussive parts.

        :param masking:           masking (see below)
        :param harmonic_filter:   tuple with harmonic filter size
                                  (frames, bins)
        :param percussive_filter: tuple with percussive filter size
                                  (frames, bins)

        Note: `masking` can be either the literal 'binary' or any float
              coefficient resulting in a soft mask. `None` translates to a
              binary mask, too.

        """
        # fetch the arguments for source separation (or set defaults)
        masking = kwargs.pop('masking', MASKING)
        harmonic_filter = kwargs.pop('harmonic_filter', HARMONIC_FILTER)
        percussive_filter = kwargs.pop('percussive_filter', PERCUSSIVE_FILTER)
        # create a Spectrogram object
        super(HarmonicPercussiveSourceSeparation, self).__init__(*args,
                                                                 **kwargs)
        # set the parameters, so they get used for computation
        self._masking = masking
        self._harmonic_filter = np.asarray(harmonic_filter, dtype=int)
        self._percussive_filter = np.asarray(percussive_filter, dtype=int)
        # init arrays
        self._harmonic = None
        self._percussive = None
        self._harmonic_slice = None
        self._percussive_slice = None

    @property
    def masking(self):
        """Masking coefficient."""
        return self._masking

    @property
    def harmonic_filter(self):
        """Harmonic filter size."""
        return self._harmonic_filter

    @property
    def percussive_filter(self):
        """Percussive filter size."""
        return self._percussive_filter

    @property
    def harmonic_slice(self):
        """Harmonic slice of the magnitude spectrogram."""
        if self._harmonic_slice is None:
            # calculate the harmonic part
            self._harmonic_slice = median_filter(self.spec,
                                                 self._harmonic_filter)
        # return
        return self._harmonic_slice

    @property
    def percussive_slice(self):
        """Percussive slice of the magnitude spectrogram."""
        if self._percussive_slice is None:
            # calculate the percussive part
            self._percussive_slice = median_filter(self.spec,
                                                   self._percussive_filter)
        # return
        return self._percussive_slice

    @property
    def harmonic_mask(self):
        """Harmonic mask for the spectrogram."""
        if self.masking in [None, 'binary']:
            # return a binary mask
            return self.harmonic_slice > self.percussive_slice
        else:
            # return a soft mask
            p = float(self.masking)
            return self.harmonic_slice ** p / (self.harmonic_slice ** p +
                                               self.percussive_slice ** p)

    @property
    def percussive_mask(self):
        """Percussive mask for the spectrogram."""
        if self.masking in [None, 'binary']:
            # return a binary mask
            return self.percussive_slice > self.harmonic_slice
        else:
            # return a soft mask
            p = float(self.masking)
            return self.percussive_slice ** p / (self.percussive_slice ** p +
                                                 self.harmonic_slice ** p)

    @property
    def harmonic(self):
        """Harmonic spectrogram."""
        if self._harmonic is None:
            # multiply the spectrogram with the harmonic mask
            self._harmonic = self.spec * self.harmonic_mask
        # return the harmonic spectrogram
        return self._harmonic

    @property
    def percussive(self):
        """Percussive spectrogram."""
        if self._percussive is None:
            # multiply the spectrogram with the percussive mask
            self._percussive = self.spec * self.percussive_mask
        # return the percussive spectrogram
        return self._percussive


HPSS = HarmonicPercussiveSourceSeparation
