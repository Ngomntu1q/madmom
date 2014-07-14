# encoding: utf-8
"""
This package includes higher level features. Your definition of "higher" may
vary, but all "lower" level features can be found the `audio` package.

"""

import numpy as np
import multiprocessing as mp
from ..audio.signal import Signal
from ..ml.rnn import process_rnn


class Activations(np.ndarray):
    """
    Activations class.

    """
    SAVE = True

    def __new__(cls, data, fps=None, sep=None):
        """
        Instantiate a new Activations object.

        :param data: either a numpy array or filename or file handle
        :param fps:  frames per second
        :return:     Activations instance

        """
        # check the type of the given data
        if isinstance(data, np.ndarray):
            # cast to Activations
            obj = np.asarray(data).view(cls)
        elif isinstance(data, (basestring, file)):
            # read from file or file handle
            obj = cls.load(data, sep)
        else:
            raise TypeError("wrong input data for Activations")
        # set frame rate
        obj.fps = fps
        # return the object
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        # set default values here
        self.fps = getattr(obj, 'fps', None)

    @classmethod
    def load(cls, filename, sep=None):
        """
        Load the activations from a file.

        :param filename: input file name or file handle
        :param sep:      separator between activation values
        :return:         Activations instance

        Note: An undefined or empty (“”) separator means that the file should
              be treated as a numpy binary file.

        """
        # load the activations
        if sep in [None, '']:
            # numpy binary format
            data = np.load(filename)
        else:
            # simple text format
            data = np.loadtxt(filename, delimiter=sep)
        # instantiate a new object
        return cls(data)

    def save(self, filename, sep=None):
        """
        Save the activations to a file.

        :param filename: output file name or file handle
        :param sep:      separator between activation values

        Note: An undefined or empty (“”) separator means that the file should
              be written as a numpy binary file.

        """
        # save the activations
        if sep in [None, '']:
            # numpy binary format
            np.save(filename, self)
        else:
            # simple text format
            np.savetxt(filename, self, fmt='%.5f', delimiter=sep)

    @staticmethod
    def add_arguments(parser):
        """
        Add options to save/load activations to an existing parser object.

        :param parser: existing argparse parser object
        :return:       input/output argument parser group object

        """
        # add onset detection related options to the existing parser
        g = parser.add_argument_group('save/load the activations')
        # add options for saving and loading the activations
        g.add_argument('-s', dest='save', action='store_true', default=False,
                       help='save the activations to file')
        g.add_argument('-l', dest='load', action='store_true', default=False,
                       help='load the activations from file')
        g.add_argument('--sep', action='store', default=None,
                       help='separator for saving/loading the activation '
                            'function [default: None, i.e. numpy binary format]')
        # return the argument group so it can be modified if needed
        return g


class EventDetection(object):
    """
    Base class for anything that detects events in an audio signal.

    """

    def __init__(self, signal, **kwargs):
        """
        Instantiate an EventDetection object from a Signal instance.

        :param signal: Signal instance or input file name or file handle
        :param kwargs: dictionary with additional arguments passed to Signal()
                       if a filename or file handle is given

        Note: the method calls the pre_process() method with the Signal to
              obtain data suitable to be further processed by the process()
              method to compute the activations.

        """
        # load the Signal
        if isinstance(Signal, Signal) or signal is None:
            # already a Signal instance
            self.signal = signal
        else:
            # try to instantiate a Signal object
            self.signal = Signal(signal, **kwargs)
        # init fps, data, activations and detections
        self._fps = None
        self._data = None
        self._activations = None
        self._detections = None

    @property
    def fps(self):
        """Frames rate."""
        if self._fps is None:
            # try to get the frame rate from the activations
            return self.activations.fps
        return self._fps

    @property
    def data(self):
        """The pre-processed data."""
        if self._data is None:
            self.pre_process()
        return self._data

    def pre_process(self):
        """
        Pre-process the signal and return data suitable for further processing.
        This method should be implemented by subclasses.

        :returns: data suitable for further processing.

        Note: The method is expected to pre-process the signal into data
              suitable for further processing and save it to self._data.
              Additionally it should return the data itself.

        """
        # functionality should be implemented by subclasses
        self._data = self.signal
        return self._data

    @classmethod
    def from_data(cls, data, fps=None):
        """
        Instantiate an EventDetection object from the given pre-processed data.

        :param data: data to be used for further processing
        :return:     EventDetection instance

        """
        # instantiate an EventDetection object (without a signal attribute)
        obj = cls(None)
        # load the data
        obj._data = data
        # set the frame rate
        if fps:
            obj._fps = fps
        # return the newly created object
        return obj

    @property
    def activations(self):
        """The activations."""
        if self._activations is None:
            self.process()
        return self._activations

    def process(self):
        """
        Process the data and compute the activations.
        This method should be implemented by subclasses.

        :returns: activations computed from the signal

        Note: The method is expected to compute the activations from the
              data and save the activations to self._activations.
              Additionally it should return the activations itself.

        """
        # functionality should be implemented by subclasses
        self._activations = self._data
        return self._activations

    @classmethod
    def from_activations(cls, activations, fps=None, sep=None):
        """
        Instantiate an EventDetection object from an Activations instance.

        :param activations: Activations instance or input file name or file
                            handle
        :param fps:         frames per second
        :return:            EventDetection instance

        """
        # instantiate an EventDetection object (without a signal attribute)
        obj = cls(None)
        # load the Activations
        if isinstance(activations, Activations):
            # already an Activations instance
            obj._activations = activations
            if fps:
                # overwrite the frame rate
                obj._activations.fps = fps
        else:
            # try to instantiate an Activations object
            obj._activations = Activations(activations, fps, sep)
        # return the newly created object
        return obj

    @property
    def detections(self):
        """The detected events."""
        if self._detections is None:
            self.detect()
        return self._detections

    def detect(self):
        """
        Extracts the events (beats, onsets, ...) from the activations.
        This method should be implemented by subclasses.

        :returns: the detected events

        Note: The method is expected to compute the detections from the
              activations and save the detections to self._detections.
              Additionally it should return the detections itself.

        """
        # functionality should be implemented by subclasses
        self._detections = self._activations
        return self._detections

    def write(self, filename):
        """
        Write the detected events to a file.

        :param filename: output file name or file handle

        """
        # TODO: refactor the write_events() function into this module?
        from ..utils import write_events
        write_events(self.detections, filename)


class RNNEventDetection(EventDetection):
    """
    Base class for anything that use RNNs to detects events in an audio signal.

    """
    NN_FILES = None
    NUM_THREADS = mp.cpu_count()

    def __init__(self, signal, nn_files=NN_FILES, num_threads=NUM_THREADS,
                 **kwargs):
        """
        Sets up the object. Check the docs in the EventDetection class for
        further parameters.

        :param signal:      see EventDetection class

        :param nn_files:    list of files that define the RNN
        :param num_threads: number of threads for rnn processing

        :param kwargs:      additional arguments passed to EventDetection()

        """

        super(RNNEventDetection, self).__init__(signal, **kwargs)

        self.nn_files = nn_files
        # self.fps = fps
        self.num_threads = num_threads
        self._data = None

    def process(self, fps=None):
        """
        Computes the predictions on the data with the RNN models defined/given.

        :param fps: frames per second of the activations
        :return:    activations

        """
        # compute the activations with RNNs
        activations = process_rnn(self.data, self.nn_files, self.num_threads)
        # save the activations
        if fps:
            self._fps = fps
        # TODO: the ravel() stuff should be removed here and
        self._activations = Activations(activations.ravel(), self.fps)
        # and return them
        return self.activations

    # TODO: move this to the ml.rnn module?
    @staticmethod
    def add_arguments(parser, nn_files=None, num_threads=NUM_THREADS):
        """
        Add neural network testing options to an existing parser object.

        :param parser:      existing argparse parser object
        :param nn_files:    list of NN files
        :param num_threads: number of threads to run in parallel
        :return:            neural network argument parser group object

        """
        # add neural network related options to the existing parser
        g = parser.add_argument_group('neural network arguments')
        g.add_argument('--nn_files', action='append', type=str,
                       default=nn_files, help='average the predictions of '
                       'these pre-trained neural networks (multiple files '
                       'can be given, one file per argument)')
        g.add_argument('--threads', dest='num_threads', action='store',
                       type=int, default=num_threads,
                       help='number of parallel threads [default=%(default)s]')
        # return the argument group so it can be modified if needed
        return g

import onsets
import beats
import tempo
