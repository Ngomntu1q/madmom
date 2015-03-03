#!/usr/bin/env python
# encoding: utf-8
"""
This file contains basic signal processing functionality.

@author: Sebastian Böck <sebastian.boeck@jku.at>

"""

import numpy as np

from madmom import Processor


# signal functions
def smooth(signal, kernel):
    """
    Smooth the signal along the first axis.

    :param signal: signal [numpy array]
    :param kernel: smoothing kernel [numpy array or int]
    :return:       smoothed signal

    Note: If `kernel` is an integer, a Hamming window of that length will be
          used as a smoothing kernel.

    """
    # check if a kernel is given
    if kernel is None:
        return signal
    # size for the smoothing kernel is given
    elif isinstance(kernel, int):
        if kernel > 1:
            # use a Hamming window of given length
            kernel = np.hamming(kernel)
        else:
            raise ValueError("can't create a smoothing window of size %d" %
                             kernel)
    # otherwise use the given smoothing kernel directly
    elif isinstance(kernel, np.ndarray):
        if len(kernel) > 1:
            kernel = kernel
    else:
        raise ValueError("can't smooth signal with %s" % kernel)
    # convolve with the kernel and return
    if signal.ndim == 1:
        return np.convolve(signal, kernel, 'same')
    elif signal.ndim == 2:
        from scipy.signal import convolve2d
        return convolve2d(signal, kernel[:, np.newaxis], 'same')
    else:
        raise ValueError('signal must be either 1D or 2D')


def attenuate(signal, attenuation):
    """"
    Attenuate the signal.

    :param signal:      signal [numpy array]
    :param attenuation: attenuation level [dB, float]
    :return:            attenuated signal

    Note: The signal is returned with the same type, thus in case of integer
          dtypes, rounding errors may occur.

    """
    # return the signal unaltered if no attenuation is given
    if attenuation == 0:
        return signal
    # FIXME: attenuating the signal and keeping the original dtype makes the
    #        following signal processing steps well-behaved, since these rely
    #        on the dtype of the array to determine the correct value range.
    #        This introduces rounding (truncating) errors in case of signals
    #        with integer dtypes. But these errors should be negligible.
    # Note: np.asanyarray returns the signal's ndarray subclass
    return np.asanyarray(signal / np.power(np.sqrt(10.), attenuation / 10.),
                         dtype=signal.dtype)


def normalize(signal):
    """
    Normalize the signal to the range -1..+1

    :param signal: signal [numpy array]
    :return:       normalized signal

    Note: The signal is always returned with np.float dtype.

    """
    # Note: np.asanyarray returns the signal's ndarray subclass
    return np.asanyarray(signal.astype(np.float) / np.max(signal))


def downmix(signal):
    """
    Down-mix the signal to mono.

    :param signal: signal [numpy array]
    :return:       mono signal

    Note: The signal is returned with the same type, thus in case of integer
          dtypes, rounding errors may occur.

    """
    # down-mix the signal and keep the original dtype if wanted
    # Note: np.asanyarray returns the signal's ndarray subclass
    if signal.ndim > 1:
        return np.mean(signal, axis=-1, dtype=signal.dtype)
    else:
        return signal


def trim(signal):
    """
    Trim leading and trailing zeros of the signal.

    :param signal: signal [numpy array]
    :return:       trimmed signal

    """
    # signal must be mono
    if signal.ndim > 1:
        # FIXME: please implement stereo (or multi-channel) handling
        #        maybe it works, haven't checked
        raise NotImplementedError("please implement multi-dim functionality")
    return np.trim_zeros(signal)


def root_mean_square(signal):
    """
    Computes the root mean square of the signal. This can be used as a
    measurement of power.

    :param signal: signal [numpy array]
    :return:       root mean square of the signal

    """
    # make sure the signal is a numpy array
    if not isinstance(signal, np.ndarray):
        raise TypeError("Invalid type for signal, must be a numpy array.")
    # signal must be mono
    if signal.ndim > 1:
        # FIXME: please implement stereo (or multi-channel) handling
        raise NotImplementedError("please implement multi-dim functionality")
    # Note: type conversion needed because of integer overflows
    if signal.dtype != np.float:
        signal = signal.astype(np.float)
    # return
    return np.sqrt(np.dot(signal, signal) / signal.size)


def sound_pressure_level(signal, p_ref=1.0):
    """
    Computes the sound pressure level of a signal.

    :param signal: signal [numpy array]
    :param p_ref:  reference sound pressure level
    :return:       sound pressure level of the signal

    From http://en.wikipedia.org/wiki/Sound_pressure:
    Sound pressure level (SPL) or sound level is a logarithmic measure of the
    effective sound pressure of a sound relative to a reference value. It is
    measured in decibels (dB) above a standard reference level.

    """
    # compute the RMS
    rms = root_mean_square(signal)
    # compute the SPL
    if rms == 0:
        # return the smallest possible negative number
        return -np.finfo(float).max
    else:
        # normal SPL computation
        return 20.0 * np.log10(rms / p_ref)


# function for automatically determining how to open audio files
def load_audio_file(filename, sample_rate=None):
    """
    Load the audio data from the given file and return it as a numpy array.

    :param filename:    name of the file or file handle
    :param sample_rate: sample rate of the signal [Hz]
    :return:            tuple (signal, sample_rate)

    """
    # determine the name of the file
    if isinstance(filename, file):
        # open file handle
        filename = filename.name
    # how to handle the file?
    if filename.endswith(".wav"):
        # wav file
        from scipy.io import wavfile
        sample_rate, signal = wavfile.read(filename, mmap=True)
    # generic signal converter
    else:
        # TODO: use sox to convert from different input signals and use the
        #       given sample rate to re-sample the signal on the fly if needed
        raise NotImplementedError('please integrate sox signal handling.')
    return signal, sample_rate


# signal classes
class Signal(np.ndarray):
    """
    Signal extends a numpy ndarray with a 'sample_rate' and some other useful
    attributes.

    """

    def __new__(cls, data, sample_rate=None):
        """
        Creates a new Signal instance.

        :param data:        numpy array
        :param sample_rate: sample rate of the signal

        """
        # try to load an audio file if the data is not a numpy array
        if not isinstance(data, np.ndarray):
            data, sample_rate = load_audio_file(data, sample_rate)
        # cast as Signal
        obj = np.asarray(data).view(cls)
        if sample_rate is not None:
            sample_rate = float(sample_rate)
        obj.sample_rate = sample_rate
        # return the object
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        # set default values here, also needed for views of the Signal
        self.sample_rate = getattr(obj, 'sample_rate', None)

    @property
    def num_samples(self):
        """Number of samples."""
        return len(self)

    @property
    def num_channels(self):
        """Number of channels."""
        try:
            # multi channel files
            return np.shape(self)[1]
        except IndexError:
            # catch mono files
            return 1

    @property
    def length(self):
        """Length of signal in seconds."""
        # n/a if the signal has no sample rate
        if self.sample_rate is None:
            return None
        return float(self.num_samples) / self.sample_rate


class SignalProcessor(Processor):
    """
    SignalProcessor is a basic signal processor.

    """
    # default values
    SAMPLE_RATE = None
    MONO = False
    NORM = False
    ATT = 0.

    def __init__(self, sample_rate=SAMPLE_RATE, mono=MONO, norm=NORM, att=ATT,
                 **kwargs):
        """
        Creates a new SignalProcessor instance.

        :param sample_rate: sample rate of the signal [Hz]
        :param mono:        down-mix the signal to mono [bool]
        :param norm:        normalize the signal [bool]
        :param att:         attenuate the signal [dB]

        """
        self.sample_rate = sample_rate
        self.mono = mono
        self.norm = norm
        self.att = att

    def process(self, data):
        """
        Processes the given signal.

        :param data: file name or handle
        :return:     Signal instance with processed signal

        """
        # instantiate a Signal (with the given sample rate if set)
        data = Signal(data, self.sample_rate)
        # process it if needed
        if self.mono:
            # down-mix to mono
            data = downmix(data)
        if self.norm:
            # normalize signal
            data = normalize(data)
        if self.att is not None and self.att != 0:
            # attenuate signal
            data = attenuate(data, self.att)
        # return processed data
        return data

    @classmethod
    def add_arguments(cls, parser, sample_rate=None, mono=None, norm=None,
                      att=None):
        """
        Add signal processing related arguments to an existing parser.

        :param parser:      existing argparse parser object
        :param sample_rate: re-sample the signal to this sample rate [Hz]
        :param mono:        down-mix the signal to mono [bool]
        :param norm:        normalize the signal [bool]
        :param att:         attenuate the signal [dB, float]
        :return:            signal processing argument parser group

        Parameters are included in the group only if they are not 'None'.

        """
        # add signal processing options to the existing parser
        g = parser.add_argument_group('signal processing arguments')
        if sample_rate is not None:
            g.add_argument('--sample_rate', action='store_true',
                           default=sample_rate,
                           help='re-sample the signal to this sample rate [Hz]')
        if mono is not None:
            g.add_argument('--mono', action='store_true', default=mono,
                           help='down-mix the signal to mono')
        if norm is not None:
            g.add_argument('--norm', action='store_true', default=norm,
                           help='normalize the signal [default=%(default)s]')
        if att is not None:
            g.add_argument('--att', action='store', type=float, default=att,
                           help='attenuate the signal '
                                '[dB, default=%(default).1f]')
        # return the argument group so it can be modified if needed
        return g


# functions for splitting a signal into frames
def signal_frame(signal, index, frame_size, hop_size, origin=0):
    """
    This function returns frame[index] of the signal.

    :param signal:     signal [numpy array]
    :param index:      index of the frame to return [int]
    :param frame_size: size of each frame in samples [int]
    :param hop_size:   hop size in samples between adjacent frames [float]
    :param origin:     location of the window center relative to the signal
                       position [int]
    :return:           the requested frame of the signal

    The first frame (index == 0) refers to the first sample of the signal, and
    each following frame is placed `hop_size` samples after the previous one.

    The window is always centered around this reference sample. Its location
    relative to the reference sample can be set with the `origin` parameter.
    Arbitrary integer values can be given:
      - zero centers the window on its reference sample
      - negative values shift the window to the right
      - positive values shift the window to the left
    An `origin` of half the size of the `frame_size` results in windows located
    to the left of the reference sample, i.e. the first frame starts at the
    first sample of the signal.

    The part of the frame which is not covered by the signal is padded with 0s.

    """
    # length of the signal
    num_samples = len(signal)
    # seek to the correct position in the audio signal
    ref_sample = int(index * hop_size)
    # position the window
    start = ref_sample - frame_size // 2 + int(origin)
    stop = start + frame_size
    # return the requested portion of the signal
    # Note: usually np.zeros_like(signal[:frame_size]) is exactly what we want
    #       (i.e. zeros of frame_size length and the same type as the signal),
    #       but since we have no guarantee that the signal is that long, we
    #       have to use the workaround of np.repeat(signal[:1] * 0, frame_size)
    if (stop < 0) or (start > num_samples):
        # window falls completely outside the actual signal, return just zeros
        frame = np.repeat(signal[:1] * 0, frame_size)
        return frame
    elif (start < 0) and (stop > num_samples):
        # window surrounds the actual signal, position signal accordingly
        frame = np.repeat(signal[:1] * 0, frame_size)
        frame[-start:num_samples - start] = signal
        return frame
    elif start < 0:
        # window crosses left edge of actual signal, pad zeros from left
        frame = np.repeat(signal[:1] * 0, frame_size)
        frame[-start:] = signal[:stop]
        return frame
    elif stop > num_samples:
        # window crosses right edge of actual signal, pad zeros from right
        frame = np.repeat(signal[:1] * 0, frame_size)
        frame[:num_samples - start] = signal[start:]
        return frame
    else:
        # normal read operation
        return signal[start:stop]


# taken from: http://www.scipy.org/Cookbook/SegmentAxis
def segment_axis(signal, frame_size, hop_size=1, axis=None, end='cut',
                 end_value=0):
    """
    Generate a new array that chops the given array along the given axis into
    (overlapping) frames.

    :param signal:     signal [numpy array]
    :param frame_size: size of each frame in samples [int]
    :param hop_size:   hop size in samples between adjacent frames [int]
    :param axis:       axis to operate on; if None, act on the flattened array
    :param end:        what to do with the last frame, if the array is not
                       evenly divisible into pieces; possible values:
                       'cut'  simply discard the extra values
                       'wrap' copy values from the beginning of the array
                       'pad'  pad with a constant value
    :param end_value:  value to use for end='pad'
    :return:           2D array with overlapping frames

    The array is not copied unless necessary (either because it is unevenly
    strided and being flattened or because end is set to 'pad' or 'wrap').

    The returned array is always of type np.ndarray.

    Example:
    >>> segment_axis(np.arange(10), 4, 2)
    array([[0, 1, 2, 3],
           [2, 3, 4, 5],
           [4, 5, 6, 7],
           [6, 7, 8, 9]])

    """
    # make sure that both frame_size and hop_size are integers
    frame_size = int(frame_size)
    hop_size = int(hop_size)
    # TODO: add comments!
    if axis is None:
        signal = np.ravel(signal)  # may copy
        axis = 0
    if axis != 0:
        raise ValueError('please check if the resulting array is correct.')

    length = signal.shape[axis]

    if hop_size <= 0:
        raise ValueError("hop_size must be positive.")
    if frame_size <= 0:
        raise ValueError("frame_size must be positive.")

    if length < frame_size or (length - frame_size) % hop_size:
        if length > frame_size:
            round_up = (frame_size + (1 + (length - frame_size) // hop_size) *
                        hop_size)
            round_down = (frame_size + ((length - frame_size) // hop_size) *
                          hop_size)
        else:
            round_up = frame_size
            round_down = 0
        assert round_down < length < round_up
        assert round_up == round_down + hop_size or (round_up == frame_size and
                                                     round_down == 0)
        signal = signal.swapaxes(-1, axis)

        if end == 'cut':
            signal = signal[..., :round_down]
        elif end in ['pad', 'wrap']:
            # need to copy
            s = list(signal.shape)
            s[-1] = round_up
            y = np.empty(s, dtype=signal.dtype)
            y[..., :length] = signal
            if end == 'pad':
                y[..., length:] = end_value
            elif end == 'wrap':
                y[..., length:] = signal[..., :round_up - length]
            signal = y

        signal = signal.swapaxes(-1, axis)

    length = signal.shape[axis]
    if length == 0:
        raise ValueError("Not enough data points to segment array in 'cut' "
                         "mode; try end='pad' or end='wrap'")
    assert length >= frame_size
    assert (length - frame_size) % hop_size == 0
    n = 1 + (length - frame_size) // hop_size
    s = signal.strides[axis]
    new_shape = (signal.shape[:axis] + (n, frame_size) +
                 signal.shape[axis + 1:])
    new_strides = (signal.strides[:axis] + (hop_size * s, s) +
                   signal.strides[axis + 1:])

    try:
        return np.ndarray.__new__(np.ndarray, strides=new_strides,
                                  shape=new_shape, buffer=signal,
                                  dtype=signal.dtype)
    except TypeError:
        # TODO: remove warning?
        import warnings
        warnings.warn("Problem with ndarray creation forces copy.")
        signal = signal.copy()
        # Shape doesn't change but strides does
        new_strides = (signal.strides[:axis] + (hop_size * s, s) +
                       signal.strides[axis + 1:])
        return np.ndarray.__new__(np.ndarray, strides=new_strides,
                                  shape=new_shape, buffer=signal,
                                  dtype=signal.dtype)


# classes for splitting a signal into frames
class FramedSignal(object):
    """
    FramedSignal splits a Signal into frames and makes it iterable and
    indexable.

    """

    def __init__(self, signal, frame_size=2048, hop_size=441., fps=None,
                 origin=0, start=0, end='extend', **kwargs):
        """
        Creates a new FramedSignal instance.

        :param signal:     Signal instance (or anything a Signal can be
                           instantiated from)
        :param frame_size: size of one frame [int]
        :param hop_size:   progress N samples between adjacent frames [float]
        :param fps:        use given frames per second (if set, this overwrites
                           the given `hop_size` value) [float]
        :param origin:     location of the window relative to the signal
                           position [int]
        :param start:      start sample [int]
        :param end:        end of signal handling (see below)

        If no Signal instance was given, one is instantiated and these
        arguments are passed:

        :param args:       additional arguments passed to Signal()
        :param kwargs:     additional keyword arguments passed to Signal()

        The FramedSignal class is implemented as an iterator. It splits
        the given Signal automatically into frames of `frame_size` length
        with `hop_size` samples (can be float, normal rounding applies)
        between the frames.

        The location of the window relative to its reference sample can be set
        with the `origin` parameter. Arbitrary integer values can be given
          - zero centers the window on its reference sample
          - negative values shift the window to the right
          - positive values shift the window to the left
        Additionally, it can have the following literal values:
          - 'center', 'offline':      the window is centered on its reference
                                      sample
          - 'left', 'past', 'online': the window is located to the left of its
                                      reference sample (including the reference
                                      sample)
          - 'right', 'future':        the window is located to the right of its
                                      reference sample

        If only a certain part of the Signal is wanted, `start` (in samples)
        and `end` (in frames) can be used to set the range accordingly.
        Additionally, the `end` parameter can have the following literal
        values:
          - 'normal': stop as soon as the whole signal got covered by at least
                      one frame, i.e. pad maximally one frame
          - 'extend': frames are returned as long as part of the frame overlaps
                      with the signal to cover the whole signal

        Note: We do not use the `frame_size` for the calculation of the number
              of frames in order to be able to stack multiple frames obtained
              with different frame sizes. Thus it is not guaranteed that every
              sample of the signal is returned in a frame if the `origin` is
              not 'right' or 'future'.

        """
        # signal handling
        if isinstance(signal, Signal):
            # already a signal
            self.signal = signal
        else:
            # try to instantiate a Signal
            self.signal = Signal(signal, **kwargs)

        # arguments for splitting the signal into frames
        if frame_size:
            self.frame_size = int(frame_size)
        if hop_size:
            self.hop_size = float(hop_size)
        # use fps instead of hop_size
        if fps:
            # overwrite the hop_size
            self.hop_size = self.signal.sample_rate / float(fps)

        # translate literal window location values to numeric origin
        if origin in ('center', 'offline'):
            # the current position is the center of the frame
            origin = 0
        elif origin in ('left', 'past', 'online'):
            # the current position is the right edge of the frame
            # this is usually used when simulating online mode, where only past
            # information of the audio signal can be used
            origin = (frame_size - 1) / 2
        elif origin in ('right', 'future'):
            # the current position is the left edge of the frame
            origin = -(frame_size / 2)
        self.origin = int(origin)

        # start position of the signal (in samples)
        self.start = int(start)

        # number of frames determination
        if end == 'extend':
            # return frames as long as a frame covers any signal
            num_frames = np.floor(len(self.signal) / float(self.hop_size) + 1)
        elif end == 'normal':
            # return frames as long as the origin sample covers the signal
            num_frames = np.ceil(len(self.signal) / float(self.hop_size))
        else:
            num_frames = end
        self.num_frames = int(num_frames)

    # make the Object indexable / iterable
    def __getitem__(self, index):
        """
        This makes the FramedSignalProcessor class indexable and/or iterable.

        The signal is split into frames (of length 'frame_size') automatically.
        Two frames are located 'hop_size' samples apart. 'hop_size' can be
        float, normal rounding applies.

        Note: Index -1 refers NOT to the last frame, but to the frame directly
              left of frame 0. Although this is contrary to common behavior,
              being able to access these frames can be important, e.g. if the
              frames overlap, frame -1 contains parts of the signal of frame 0.

        """
        # a single index is given
        if isinstance(index, int):
            # return a single frame
            if index < self.num_frames:
                # return the frame at this index
                # subtract the origin from the start position and use as offset
                return signal_frame(self.signal, index,
                                    frame_size=self.frame_size,
                                    hop_size=self.hop_size,
                                    origin=(self.start - self.origin))
            # otherwise raise an error to indicate the end of signal
            raise IndexError("end of signal reached")
        # a slice is given
        elif isinstance(index, slice):
            # determine the frames to return
            start, stop, step = index.indices(self.num_frames)
            # allow only normal steps
            if step != 1:
                raise ValueError('only slices with a step size of 1 supported')
            # determine the number of frames
            num_frames = stop - start
            # determine the start sample
            start_sample = self.start + self.hop_size * start
            # return a new FramedSignalProcessor instance covering the requested frames
            return FramedSignal(self.signal, frame_size=self.frame_size,
                                hop_size=self.hop_size, origin=self.origin,
                                start=start_sample, num_frames=num_frames)
        # other index types are invalid
        else:
            raise TypeError("frame indices must be slices or integers")

    # len() returns the number of frames, consistent with __getitem__()
    def __len__(self):
        return self.num_frames

    @property
    def frame_rate(self):
        """Frame rate."""
        # n/a if the signal has no sample rate
        if self.signal.sample_rate is None:
            return None
        return float(self.signal.sample_rate) / self.hop_size

    @property
    def fps(self):
        """Frames per second."""
        return self.frame_rate

    @property
    def overlap_factor(self):
        """Overlapping factor of two adjacent frames."""
        return 1.0 - self.hop_size / self.frame_size

    @property
    def shape(self):
        """Shape of the FramedSignal (frames x samples)."""
        return self.num_frames, self.frame_size


class FramedSignalProcessor(Processor):
    """
    Slice a Signal into frames.

    """
    # default values for splitting a signal into overlapping frames
    FRAME_SIZE = 2048
    HOP_SIZE = 441.
    FPS = 100.
    ONLINE = False
    START = 0
    END_OF_SIGNAL = 'extend'

    def __init__(self, frame_size=FRAME_SIZE, hop_size=HOP_SIZE, fps=None,
                 online=ONLINE, end=END_OF_SIGNAL, **kwargs):
        """
        Creates a new FramedSignalProcessor instance.

        :param frame_size: size of one frame in samples [int]
        :param hop_size:   progress N samples between adjacent frames [float]
        :param fps:        use frames per second (compute the needed `hop_size`
                           instead of using the given `hop_size` value) [float]
        :param online:     operate in online mode (see below) [bool]
        :param end:        end of signal handling (see below)

        The location of the window relative to its reference sample can be set
        with the `online` parameter:
          - 'True':  the window is located to the left of its reference sample
                     (including the reference sample), i.e. only past
                     information is used
          - 'False': the window is centered on its reference sample [default]

        The end of the signal handling can be set with the `end` parameter,
        it accepts the following literal values:
          - 'normal': the origin of the last frame has to be within the signal
          - 'extend': frames are returned as long as part of the frame overlaps
                      with the signal [default]

        """
        self.frame_size = frame_size
        self.hop_size = hop_size
        self.fps = fps  # do not convert here, pass it to FramedSignal
        self.online = online
        self.end = end

    def process(self, data, start=0, num_frames=None):
        """
        Slice the signal into (overlapping) frames.

        :param data:       signal to be sliced into frames [Signal]
        :param start:      start sample [int]
        :param num_frames: limit the number of frames to be returned [int]
        :return:           FramedSignal instance

        Note: If `num_frames` is 'None', the length of the returned signal is
              determined by the `end_of_signal` setting.

        """
        # how many frames to process?
        if num_frames is None:
            num_frames = self.end
        # translate online / offline mode
        if self.online:
            origin = 'online'
        else:
            origin = 'offline'
        # instantiate a FramedSignal from the data and return it
        return FramedSignal(data, frame_size=self.frame_size,
                            hop_size=self.hop_size, fps=self.fps,
                            origin=origin, start=start, end=num_frames)

    @classmethod
    def add_arguments(cls, parser, frame_size=FRAME_SIZE, fps=FPS,
                      online=ONLINE):
        """
        Add signal framing related arguments to an existing parser.

        :param parser:     existing argparse parser object
        :param frame_size: size of one frame in samples [int]
        :param fps:        frames per second [float]
        :param online:     online mode [bool]
        :return:           signal framing argument parser group

        Parameters are included in the group only if they are not 'None'.

        """
        # add signal framing options to the existing parser
        g = parser.add_argument_group('signal framing arguments')
        if frame_size is not None:
            # depending on the type, use different options
            if isinstance(frame_size, int):
                g.add_argument('--frame_size', action='store', type=int,
                               default=frame_size,
                               help='frame size [samples, default=%(default)i]')
            elif isinstance(frame_size, list):
                from madmom.utils import OverrideDefaultListAction
                g.add_argument('--frame_size', type=int, default=frame_size,
                               action=OverrideDefaultListAction,
                               help='frame size(s) to use, multiple values '
                                    'be given, one per argument. [samples, '
                                    'default=%(default)s]')
        if fps is not None:
            g.add_argument('--fps', action='store', type=float, default=fps,
                           help='frames per second [default=%(default).1f]')
        if online is not None:
            g.add_argument('--online', dest='online', action='store_true',
                           default=online,
                           help='operate in online mode [default=%(default)s]')

        # TODO: include end_of_signal handling!?
        # return the argument group so it can be modified if needed
        return g
