# encoding: utf-8
"""
This package is used internally by the Department of Computational Perception,
Johannes Kepler University, Linz, Austria (http://www.cp.jku.at) and the
Austrian Research Institute for Artificial Intelligence (OFAI), Vienna, Austria
(http://www.ofai.at).

All features should be implemented as classes which inherit from Processor
(or provide a XYProcessor(Processor) variant). This way, multiple Processor
objects can be chained to achieve the wanted functionality.

Please see the README for further details of this module.

@author: Sebastian Böck <sebastian.boeck@jku.at>

"""
import os
import abc

from madmom.utils import open


MODELS_PATH = '%s/models' % (os.path.dirname(__file__))


class Processor(object):
    """
    Abstract base class for processing data.

    """
    __metaclass__ = abc.ABCMeta

    @classmethod
    def load(cls, infile):
        """
        Instantiate a new Processor from a file.

        This method un-pickles a saved Processor object. Subclasses should
        overwrite this method with a better performing solution if speed is an
        issue.

        :param infile: file name or file handle
        :return:       Processor instance

        """
        import cPickle
        # instantiate a new object and return it
        return cPickle.load(open(infile))

    def save(self, outfile):
        """
        Save the Processor to a file.

        This method pickles a Processor object and saves it. Subclasses should
        overwrite this method with a better performing solution if speed is an
        issue.

        :param outfile: output file name or file handle

        """
        import cPickle
        # save the Processor object to a file
        cPickle.dump(self, open(outfile, 'rw'))

    @abc.abstractmethod
    def process(self, data):
        """
        Process the data.

        This method must be implemented by the derived class and should
        process the given data and return the processed output.

        :param data: data to be processed
        :return:     processed data

        """
        return data


class OutputProcessor(Processor):
    """
    Class for processing data and/or feeding it into some sort of output.

    """

    @abc.abstractmethod
    def process(self, data, output):
        """
        Processes the data and feeds it to output.

        :param data:   data to be processed (e.g. written to file)
        :param output: output file name or file handle
        :return:       also return the processed data

        """
        # also return the data!
        return data


def _process(process_tuple):
    """
    Function to process a Processor object (first tuple item) with the given
    data (second tuple item). Instead of a Processor also a function accepting
    a single argument (data) and returning the processed data can be given.

    :param process_tuple: tuple (Processor/function, data)
    :return:              processed data

    Note: This must be a top-level function to be pickle-able.

    """
    # process depending whether it is a Processor or a simple function
    if isinstance(process_tuple[0], Processor):
        # call the process method
        return process_tuple[0].process(process_tuple[1])
    else:
        # simply call the function
        return process_tuple[0](process_tuple[1])


class SequentialProcessor(Processor):
    """
    Class for sequential processing of data.

    """
    def __init__(self, processors):
        """
        Instantiates a SequentialProcessor object.

        :param processors: list with Processor objects

        """
        # wrap the processor in a list if needed
        if isinstance(processors, Processor):
            processors = [processors]
        # save the processors
        self.processors = processors

    def process(self, data):
        """
        Process the data sequentially.

        :param data: data to be processed
        :return:     processed data

        """
        # sequentially process the data
        for processor in self.processors:
            data = _process((processor, data))
        return data

    def append(self, other):
        """
        Append a processor to the processing chain.

        :param other: the Processor to be appended.

        """
        self.processors.append(other)

    def extend(self, other):
        """
        Extend the processing chain with a list of Processors.

        :param other: the Processors to be appended.

        """
        self.processors.extend(other)


# inherit from SequentialProcessor because of append() and extend()
class ParallelProcessor(SequentialProcessor):
    """
    Base class for parallel processing of data.

    """
    import multiprocessing as mp
    NUM_THREADS = mp.cpu_count()

    def __init__(self, processors, num_threads=NUM_THREADS):
        """
        Instantiates a ParallelProcessor object.

        :param processors:  list with processing objects
        :param num_threads: number of parallel working threads

        """
        # save the processing queue
        super(ParallelProcessor, self).__init__(processors)
        # number of threads
        if num_threads is None:
            num_threads = 1
        self.num_threads = num_threads

    def process(self, data, num_threads=None):
        """
        Process the data in parallel.

        :param data:        data to be processed
        :param num_threads: number of parallel working threads
        :return:            list with individually processed data

        """
        import multiprocessing as mp
        import itertools as it
        # number of threads
        if num_threads is None:
            num_threads = self.num_threads
        # init a pool of workers (if needed)
        map_ = map
        if min(len(self.processors), max(1, num_threads)) != 1:
            map_ = mp.Pool(num_threads).map
        # process data in parallel and return a list with processed data
        return map_(_process, it.izip(self.processors, it.repeat(data)))

    @classmethod
    def add_arguments(cls, parser, num_threads=NUM_THREADS):
        """
        Add parallel processing options to an existing parser object.

        :param parser:      existing argparse parser object
        :param num_threads: number of threads to run in parallel [int]
        :return:            parallel processing argument parser group

        Note: A value of 0 or negative numbers for `num_threads` suppresses the
              inclusion of the parallel option. Instead 'None' is returned.
              Setting `num_threads` to 'None' sets the number equal to the
              number of available CPU cores.

        """
        if num_threads is None:
            num_threads = cls.NUM_THREADS
        # do not include the group
        if num_threads <= 0:
            return None
        # add parallel processing options
        g = parser.add_argument_group('parallel processing arguments')
        g.add_argument('-j', '--threads', dest='num_threads',
                       action='store', type=int, default=num_threads,
                       help='number of parallel threads [default=%(default)s]')
        # return the argument group so it can be modified if needed
        return g


class IOProcessor(Processor):
    """
    Input/Output Processor which processes the input data with the input
    Processor and feeds everything into the given output Processor.

    """

    def __init__(self, input_processor, output_processor):
        """
        Creates a IOProcessor instance.

        :param input_processor:  Processor or list or function
        :param output_processor: OutputProcessor or function

        Note: `input_processor` can be a Processor (or subclass thereof) or a
              function accepting a single argument (data) or a list thereof
              which gets wrapped as a SequentialProcessor.

              `output_processor` can be a OutputProcessor or a function
              accepting two arguments (data, output)

        """
        if isinstance(input_processor, list):
            self.input_processor = SequentialProcessor(input_processor)
        else:
            self.input_processor = input_processor
        self.output_processor = output_processor

    def process(self, data, output):
        """
        Processes the data with the input Processor and outputs everything into
        the output Processor.

        :param data:   input data or file to be loaded
                       [numpy array or file name or file handle]
        :param output: output file [file name or file handle]
        :return:       Activations instance

        """
        # process the input data
        data = _process((self.input_processor, data))
        # process it with the output Processor and return it
        if isinstance(self.output_processor, Processor):
            # call the process method
            return self.output_processor.process(data, output)
        else:
            # or simply call the function
            return self.output_processor(data, output)
