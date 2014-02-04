#!/usr/bin/env python
# encoding: utf-8
"""
This file contains spectrogram related functionality.

@author: Sebastian Böck <sebastian.boeck@jku.at>

"""

import numpy as np
import scipy.fftpack as fft


def stft(x, window, hop_size, offset=0, phase=False, fft_size=None):
    """
    Calculates the Short-Time-Fourier-Transform of the given signal.

    :param x:        discrete signal (1D numpy array)
    :param window:   window function (1D numpy array)
    :param hop_size: the hop size in samples between adjacent frames [float]
    :param offset:   position of the first sample inside the signal [int]
    :param phase:    circular shift for correct phase [bool]
    :param fft_size: use given size for FFT [int, should be a power of 2]
    :returns:        the complex STFT of the signal

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
    fft_bins = fft_size >> 1
    # init stft matrix
    stft = np.zeros([frames, fft_bins], np.complex64)
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
        stft[frame] = fft.fft(fft_signal, fft_size)[:fft_bins]
        # next frame
    # return
    return stft


def strided_stft(signal, window, hop_size, phase=True):
    """
    Calculates the Short-Time-Fourier-Transform of the given signal.

    :param signal:   the discrete signal
    :param window:   window function
    :param hop_size: the hop size in samples between adjacent frames [int]
    :param phase:    circular shift for correct phase [bool]
    :returns:        the complex STFT of the signal

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


# Spectrogram defaults
FILTERBANK = None
LOG = False         # default: linear spectrogram
MUL = 1
ADD = 1
NORM_WINDOW = False
FFT_SIZE = None
RATIO = 0.5
DIFF_FRAMES = None


class Spectrogram(object):
    """
    Spectrogram Class.

    """
    def __init__(self, frames, window=np.hanning, filterbank=FILTERBANK,
                 log=LOG, mul=MUL, add=ADD, norm_window=NORM_WINDOW,
                 fft_size=FFT_SIZE, ratio=RATIO, diff_frames=DIFF_FRAMES,
                 *args, **kwargs):
        """
        Creates a new Spectrogram object instance of the given audio.

        :param frames: a FramedSignal object, or a file name or file handle
        :param window: window function

        Magnitude spectrogram manipulation parameters:

        :param filterbank: filterbank used for dimensionality reduction of the
                           magnitude spectrogram

        :param log: take the logarithm of the magnitude [bool]
        :param mul: multiplier before taking the logarithm of the magnitude
        :param add: add this value before taking the logarithm of the magnitude

        Additional computations:

        :param stft:  save the raw complex STFT [bool]
        :param phase: save the phase information [bool]
        :param lgd:   save the local group delay information [bool]

        FFT parameters:

        :param norm_window: set area of window function to 1 [bool]
        :param fft_size:    use this size for FFT [int, should be a power of 2]

        Diff parameters:

        :param ratio:       calculate the difference to the frame which window
                            overlaps to this ratio [float]
        :param diff_frames: calculate the difference to the N-th previous frame
                            [int] (if set, this overrides the value calculated
                            from the ratio)

        Note: including phase and/or local group delay information slows down
              calculation considerably (phase: *2; lgd: *3)!

        """
        from .signal import FramedSignal
        # audio signal stuff
        if isinstance(frames, Spectrogram):
            # already a Spectrogram object, copy the attributes (which can be
            # overwritten by passing other values to the constructor)
            self._frames = frames.frames
            self._window = frames.window
            self._fft_size = frames.fft_size
            self._filterbank = frames.filterbank
            self._log = frames.log
            self._mul = frames.mul
            self._add = frames.add
            self._ratio = frames.ratio
            # do not copy diff_frames, it is calculated or set manually
        elif isinstance(frames, FramedSignal):
            # already a FramedSignal
            self._frames = frames
        else:
            # try to instantiate a Framed object
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
            return self.filterbank.bands

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

    def compute_stft(self, stft=None, phase=None, lgd=None):
        """
        This is a memory saving method to batch-compute different spectrograms.

        :param stft:  save the raw complex STFT to the "stft" attribute
        :param phase: save the phase of the STFT to the "phase" attribute
        :param lgd:   save the local group delay of the STFT to the "lgd"
                      attribute

        """
        # init spectrogram matrix
        spec = np.zeros([self.num_frames, self.num_fft_bins], np.float32)
        # STFT matrix
        if stft:
            self._stft = np.zeros_like(spec, dtype=np.complex64)
        # phase matrix
        if phase:
            self._phase = np.zeros_like(spec, dtype=np.float32)
        # local group delay matrix
        if lgd:
            np.zeros_like(spec, dtype=np.float32)

        # calculate DFT for all frames
        for f in range(len(self.frames)):
            # multiply the signal frame with the window function
            signal = np.multiply(self.frames[f], self._fft_window)
            # only shift and perform complex DFT if needed
            if stft or phase or lgd:
                # circular shift the signal (needed for correct phase)
                signal = np.concatenate((signal[self.num_fft_bins:],
                                         signal[:self.num_fft_bins]))
            # perform DFT
            dft = fft.fft(signal, self.fft_size)[:self.num_fft_bins]

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

            # magnitude spectrogram
            spec[f] = np.abs(dft)

        # filter with the given filterbank if needed
        if self.filterbank is not None:
            self._spec = np.dot(spec, self.filterbank)
        else:
            self._spec = spec
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
        return self.diff * (self.diff > 0)

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
        :returns:          the whitened magnitude spectrogram

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


class FilteredSpectrogram(Spectrogram):
    """
    FilteredSpectrogram is a subclass of Spectrogram which filters the
    magnitude spectrogram based on the given filterbank.

    """
    def __init__(self, *args, **kwargs):
        """
        Creates a new FilteredSpectrogram object instance.

        :param filterbank: filterbank for dimensionality reduction

        If no filterbank is given, one with the following parameters is created
        automatically:

        :param bands_per_octave: number of filter bands per octave
        :param fmin:             the minimum frequency [Hz]
        :param fmax:             the maximum frequency [Hz]
        :param norm_filters:     normalize the filter to area 1 [bool]
        :param a4:               tuning frequency of A4 [Hz]

        """
        from filterbank import (LogarithmicFilterBank, BANDS_PER_OCTAVE, FMIN,
                                FMAX, NORM_FILTERS)
        # fetch the arguments for filterbank creation (or set defaults)
        fb = kwargs.pop('filterbank', None)
        bands_per_octave = kwargs.pop('bands_per_octave', BANDS_PER_OCTAVE)
        fmin = kwargs.pop('fmin', FMIN)
        fmax = kwargs.pop('fmax', FMAX)
        norm_filters = kwargs.pop('norm_filters', NORM_FILTERS)
        # create Spectrogram object
        super(FilteredSpectrogram, self).__init__(*args, **kwargs)
        # if no filterbank was given, create one
        if fb is None:
            sample_rate = self.frames.signal.sample_rate
            fb = LogarithmicFilterBank(fft_bins=self.num_fft_bins,
                                       sample_rate=sample_rate,
                                       bands_per_octave=bands_per_octave,
                                       fmin=fmin, fmax=fmax, norm=norm_filters)
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
        Creates a new LogarithmicFilteredSpectrogram object instance.

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
        Creates a new HarmonicPercussiveSourceSeparation object instance.

        The magnitude spectrogram are separated with median filters with the
        given sizes into their harmonic and percussive parts.

        :param harmonic_filter:   tuple with harmonic filter size
                                  (frames, bins)
        :param percussive_filter: tuple with percussive filter size
                                  (frames, bins)

        """
        # fetch the arguments for separating the magnitude (or set defaults)
        harmonic_filter = kwargs.pop('harmonic_filter', HARMONIC_FILTER)
        percussive_filter = kwargs.pop('percussive_filter', PERCUSSIVE_FILTER)
        # create a Spectrogram object
        super(HarmonicPercussiveSourceSeparation, self).__init__(*args,
                                                                 **kwargs)
        # set the parameters, so they get used for computation
        self._harmonic_filter = harmonic_filter
        self._percussive_filter = percussive_filter
        # init arrays
        self._harmonic = None
        self._percussive = None

    @property
    def harmonic_filter(self):
        """Harmonic filter size."""
        return self._harmonic_filter

    @property
    def percussive_filter(self):
        """Percussive filter size."""
        return self._percussive_filter

    @property
    def harmonic(self):
        """Harmonic part of the magnitude spectrogram."""
        if self._harmonic is None:
            # calculate the harmonic part
            self._harmonic = median_filter(self.spec, self._harmonic_filter)
        # return
        return self._harmonic

    @property
    def percussive(self):
        """Percussive part of the magnitude spectrogram."""
        if self._percussive is None:
            # calculate the percussive part
            self._percussive = median_filter(self.spec,
                                             self._percussive_filter)
        # return
        return self._percussive


HPSS = HarmonicPercussiveSourceSeparation
