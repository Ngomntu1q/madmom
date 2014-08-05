# encoding: utf-8
"""
This file contains the speed crucial Viterbi functionality.

@author: Filip Korzeniowski <filip.korzeniowski@jku.at>
@author: Sebastian Böck <sebastian.boeck@jku.at>

"""
import numpy as np
cimport numpy as np
cimport cython
from libc.math cimport log

# parallel processing stuff
from cython.parallel cimport prange
import multiprocessing as mp
NUM_THREADS = mp.cpu_count()


@cython.cdivision(True)
@cython.boundscheck(False)
@cython.wraparound(False)
def crf_viterbi(float [::1] pi, float[::1] transition, float[::1] norm_factor,
                float [::1] activations, int tau):
    """
    Viterbi algorithm to compute the most likely beat sequence from the
    given activations and the dominant interval.

    :param pi:          initial distribution
    :param transition:  transition distribution
    :param norm_factor: normalisation factors
    :param activations: beat activations
    :param tau:         dominant interval [frames]
    :return:            tuple with extracted beat positions [frame indices]
                        and log probability of beat sequence

    """
    # number of states
    cdef int num_st = activations.shape[0]
    # number of transitions
    cdef int num_tr = transition.shape[0]
    # number of beat variables
    cdef int num_x = num_st / tau

    # current viterbi variables
    cdef float [::1] v_c = np.empty(num_st, dtype=np.float32)
    # previous viterbi variables. will be initialised with prior (first beat)
    cdef float [::1] v_p = np.empty(num_st, dtype=np.float32)
    # back-tracking pointers;
    cdef long [:, ::1] bps = np.empty((num_x - 1, num_st), dtype=np.int)
    # back tracked path, a.k.a. path sequence
    cdef long [::1] path = np.empty(num_x, dtype=np.int)

    # counters etc.
    cdef int k, i, j, next_state
    cdef double new_prob, sum_k, path_prob, log_sum = 0.0

    # init first beat
    for i in range(num_st):
        v_p[i] = pi[i] * activations[i]
        sum_k += v_p[i]
    for i in range(num_st):
        v_p[i] = v_p[i] / sum_k

    sum_k = 0

    # iterate over all beats; the 1st beat is given by prior
    for k in range(num_x - 1):
        # reset all current viterbi variables
        for i in range(num_st):
            v_c[i] = 0.0

        # find the best transition for each state
        for i in range(num_st):
            for j in range(num_tr):
                if (i - j) < 0:
                    break

                new_prob = v_p[i - j] * transition[j] * activations[i] * \
                           norm_factor[i - j]

                if new_prob > v_c[i]:
                    v_c[i] = new_prob
                    bps[k, i] = i - j

        sum_k = 0.0
        for i in range(num_st):
            sum_k += v_c[i]
        for i in range(num_st):
            v_c[i] /= sum_k

        log_sum += log(sum_k)

        v_p, v_c = v_c, v_p

    # add the final best state to the path
    path_prob = 0.0
    for i in range(num_st):
        if v_p[i] > path_prob:
            next_state = i
            path_prob = v_p[i]
    path[num_x - 1] = next_state

    # track the path backwards
    for i in range(num_x - 2, -1, -1):
        next_state = bps[i, next_state]
        path[i] = next_state

    # return the best sequence and its log probability
    return np.asarray(path), log(path_prob) + log_sum


cdef class BeatTrackingDynamicBayesianNetwork(object):
    """
    Dynamic Bayesian network for beat tracking.

    """
    # define some class variables which are also exported as Python attributes
    cdef readonly unsigned int num_beat_states
    cdef readonly np.ndarray tempo_states
    cdef readonly double tempo_change_probability
    cdef readonly unsigned int observation_lambda
    cdef readonly double path_probability
    cdef readonly unsigned int num_threads
    cdef readonly np.ndarray observations
    cdef readonly bint correct
    cdef readonly bint norm_observations
    # internal variable
    cdef np.ndarray _path

    # default values for beat tracking
    NUM_BEAT_STATES = 1280
    TEMPO_CHANGE_PROBABILITY = 0.008
    OBSERVATION_LAMBDA = 16
    TEMPO_STATES = np.arange(11, 47)
    CORRECT = True
    NORM_OBSERVATIONS = False

    def __init__(self, observations=None, num_beat_states=NUM_BEAT_STATES,
                 tempo_states=TEMPO_STATES,
                 tempo_change_probability=TEMPO_CHANGE_PROBABILITY,
                 observation_lambda=OBSERVATION_LAMBDA,
                 norm_observations=NORM_OBSERVATIONS,
                 correct=CORRECT, num_threads=NUM_THREADS):
        """
        Construct a new dynamic Bayesian network suitable for multi-model beat
        tracking.

        :param observations:             observations
        :param num_beat_states:          number of beat states for one beat
                                         period
        :param tempo_states:             array with tempo states (number of
                                         beat states to progress from one
                                         observation value to the next one)
        :param tempo_change_probability: probability of a tempo change from
                                         one observation to the next one
        :param observation_lambda:       split one beat period into N parts,
                                         the first representing beat states
                                         and the remaining non-beat states
        :param norm_observations:        normalise the observations
        :param correct:                  correct the detected beat positions
        :param num_threads:              number of parallel threads

        """
        # save given variables
        if observations is not None:
            self.observations = np.ascontiguousarray(observations,
                                                     dtype=np.float32)
        self.num_beat_states = num_beat_states
        self.tempo_states = np.ascontiguousarray(tempo_states, dtype=np.int32)
        self.tempo_change_probability = tempo_change_probability
        self.observation_lambda = observation_lambda
        self.num_threads = num_threads
        self.correct = correct
        self.norm_observations = norm_observations

    @cython.cdivision(True)
    @cython.boundscheck(False)
    @cython.wraparound(False)
    def viterbi(self, observations):
        """
        Determine the best path given the observations.

        :param observations: the observations (anything that can be casted to
                             a numpy array)
        :return:             most probable state-space path sequence for the
                             given observations

        Note: a uniform prior distribution is assumed.

        """
        # save the given observations as an contiguous array
        self.observations = np.ascontiguousarray(observations)
        # typed memoryview thereof
        # Note: the ::1 notation indicates that is memory contiguous
        cdef float [::1] observations_ = self.observations
        # normalise the observations memoryview, not the observations itself
        if self.norm_observations:
            observations_ = self.observations / np.max(self.observations)
        # number of observations
        cdef unsigned int num_observations = len(observations)
        # cache class/instance variables needed in the loops
        cdef double tempo_change_probability = self.tempo_change_probability
        cdef unsigned int observation_lambda = self.observation_lambda
        cdef unsigned int num_threads = self.num_threads
        cdef unsigned int num_beat_states = self.num_beat_states
        # typed memoryview of tempo states
        cdef int [::1] tempo_states_ = self.tempo_states
        cdef unsigned int num_tempo_states = len(self.tempo_states)
        # number of states
        cdef unsigned int num_states = num_beat_states * len(self.tempo_states)
        # check that the number of states fit into unsigned int16
        if num_states > np.iinfo(np.uint16).max:
            raise AssertionError('DBN can handle only %i states, not %i' %
                                 (np.iinfo(np.uint16).max, num_states))
        # current viterbi variables
        current_viterbi = np.empty(num_states, dtype=np.float)
        # typed memoryview thereof
        cdef double [::1] current_viterbi_ = current_viterbi
        # previous viterbi variables, init them with 1s as prior distribution
        # TODO: allow other priors
        prev_viterbi = np.ones(num_states, dtype=np.float)
        # typed memoryview thereof
        cdef double [::1] prev_viterbi_ = prev_viterbi
        # back-tracking pointers
        back_tracking_pointers = np.empty((num_observations, num_states),
                                           dtype=np.uint16)
        # typed memoryview thereof
        cdef unsigned short [:, ::1] back_tracking_pointers_ = \
            back_tracking_pointers
        # back tracked path, a.k.a. path sequence
        path = np.empty(num_observations, dtype=np.uint16)

        # define counters etc.
        cdef unsigned int prev_state, beat_state, tempo_state, tempo
        cdef double obs, transition_prob, viterbi_sum, path_probability = 0.0
        cdef double same_tempo_prob = 1. - tempo_change_probability
        cdef double change_tempo_prob = 0.5 * tempo_change_probability
        cdef unsigned int beat_no_beat = num_beat_states / observation_lambda
        cdef int state, frame
        # iterate over all observations
        for frame in range(num_observations):
            # search for best transitions
            for state in prange(num_states, nogil=True, schedule='static',
                                num_threads=num_threads):
                # reset the current viterbi variable
                current_viterbi_[state] = 0.0
                # position inside beat & tempo
                beat_state = state % num_beat_states
                tempo_state = state / num_beat_states
                tempo = tempo_states_[tempo_state]
                # get the observation
                if beat_state < beat_no_beat:
                    obs = observations_[frame]
                else:
                    obs = (1. - observations_[frame]) / \
                          (observation_lambda - 1)
                # for each state check the 3 possible transitions
                # previous state with same tempo
                # Note: we add num_beat_states before the modulo operation so
                #       that it can be computed in C (which is faster)
                prev_state = ((beat_state + num_beat_states - tempo) %
                              num_beat_states +
                              (tempo_state * num_beat_states))
                # probability for transition from same tempo
                transition_prob = (prev_viterbi_[prev_state] *
                                   same_tempo_prob * obs)
                # if this transition probability is greater than the current
                # one, overwrite it and save the previous state in the current
                # pointers
                if transition_prob > current_viterbi_[state]:
                    current_viterbi_[state] = transition_prob
                    back_tracking_pointers_[frame, state] = prev_state
                # transition from slower tempo
                if tempo_state > 0:
                    # previous state with slower tempo
                    # Note: we add num_beat_states before the modulo operation
                    #       so that it can be computed in C (which is faster)
                    prev_state = ((beat_state + num_beat_states -
                                   (tempo - 1)) % num_beat_states +
                                  ((tempo_state - 1) * num_beat_states))
                    # probability for transition from slower tempo
                    transition_prob = (prev_viterbi_[prev_state] *
                                       change_tempo_prob * obs)
                    if transition_prob > current_viterbi_[state]:
                        current_viterbi_[state] = transition_prob
                        back_tracking_pointers_[frame, state] = prev_state
                # transition from faster tempo
                if tempo_state < num_tempo_states - 1:
                    # previous state with faster tempo
                    # Note: we add num_beat_states before the modulo operation
                    #       so that it can be computed in C (which is faster)
                    prev_state = ((beat_state + num_beat_states -
                                   (tempo + 1)) % num_beat_states +
                                  ((tempo_state + 1) * num_beat_states))
                    # probability for transition from faster tempo
                    transition_prob = (prev_viterbi_[prev_state] *
                                       change_tempo_prob * obs)
                    if transition_prob > current_viterbi_[state]:
                        current_viterbi_[state] = transition_prob
                        back_tracking_pointers_[frame, state] = prev_state
            # overwrite the old states with the normalised current ones
            # Note: this is faster than unrolling the loop! But it is a bit
            #       tricky: we need to do the normalisation on the numpy
            #       array but do the assignment on the memoryview
            viterbi_sum = current_viterbi.sum()
            prev_viterbi_ = current_viterbi / viterbi_sum
            # add the log sum of all viterbi variables to the overall sum
            path_probability += log(viterbi_sum)

        # fetch the final best state
        state = current_viterbi.argmax()
        # add its log probability to the sum
        path_probability += log(current_viterbi.max())
        # track the path backwards, start with the last frame and do not
        # include the back_tracking_pointers for frame 0, since it includes
        # the transitions to the prior distribution states
        for frame in range(num_observations -1, -1, -1):
            # save the state in the path
            path[frame] = state
            # fetch the next previous one
            state = back_tracking_pointers[frame, state]
        # save the tracked path and log sum and return them
        self._path = path
        self.path_probability = path_probability
        return path, path_probability

    @property
    def path(self):
        """Best path sequence."""
        if self._path is None:
            self.viterbi(self.observations)
        return self._path

    @property
    def beat_states_path(self):
        """Beat states path."""
        return self.path % self.num_beat_states

    @property
    def tempo_states_path(self):
        """Tempo states path."""
        return self.tempo_states[self.path / self.num_beat_states]

    @property
    def beats(self):
        # correct the beat positions
        """The detected beats."""
        if self.correct:
            beats = []
            # for each detection determine the "beat range", i.e. states <=
            # num_beat_states / observation_lambda and choose the frame with
            # the highest observation value
            beat_range = self.beat_states_path < (self.num_beat_states /
                                                  self.observation_lambda)
            # get all change points between True and False
            idx = np.nonzero(np.diff(beat_range))[0] + 1
            # if the first frame is in the beat range, prepend a 0
            if beat_range[0]:
                idx = np.r_[0, idx]
            # if the last frame is in the beat range, append the length of the
            # array
            if beat_range[-1]:
                idx = np.r_[idx, beat_range.size]
            # iterate over all regions
            for left, right in idx.reshape((-1, 2)):
                beats.append(np.argmax(self.observations[left:right]) + left)
            beats = np.asarray(beats)
        else:
            # just take the frames with the smallest beat state values
            from scipy.signal import argrelmin
            beats = argrelmin(self.beat_states_path, mode='wrap')[0]
            # recheck if they are within the "beat range", i.e. the
            # beat states < number of beat states / observation lambda
            # Note: interpolation and alignment of the beats to be at state 0
            #       does not improve results over this simple method
            beats = beats[self.beat_states_path[beats] <
                          (self.num_beat_states / self.observation_lambda)]
        return beats

    @classmethod
    def add_arguments(cls, parser, num_beat_states=NUM_BEAT_STATES,
                      tempo_states=TEMPO_STATES,
                      tempo_change_probability=TEMPO_CHANGE_PROBABILITY,
                      observation_lambda=OBSERVATION_LAMBDA,
                      correct=CORRECT, norm_observations=NORM_OBSERVATIONS):
        """
        Add dynamic Bayesian network related arguments to an existing parser
        object.

        :param parser:                   existing argparse parser object
        :param num_beat_states:          number of cells for one beat period
        :param tempo_states:             list with tempo states
        :param tempo_change_probability: probability of a tempo change between
                                         two adjacent observations
        :param observation_lambda:       split one beat period into N parts,
                                         the first representing beat states
                                         and the remaining non-beat states
        :param correct:                  correct the beat positions
        :param norm_observations:        normalise the observations of the DBN
        :return:                         beat argument parser group object

        """
        # add a group for DBN parameters
        g = parser.add_argument_group('dynamic Bayesian Network arguments')
        g.add_argument('--num_beat_states', action='store', type=int,
                       default=num_beat_states,
                       help='number of beat states for one beat period '
                            '[default=%(default)i]')
        g.add_argument('--tempo_change_probability', action='store',
                       type=float, default=tempo_change_probability,
                       help='probability of a tempo between two adjacent '
                            'observations [default=%(default).4f]')
        g.add_argument('--observation_lambda', action='store', type=int,
                       default=observation_lambda,
                       help='split one beat period into N parts, the first '
                            'representing beat states and the remaining '
                            'non-beat states [default=%(default)i]')
        if tempo_states is not None:
            from ..utils import OverrideDefaultListAction
            g.add_argument('--tempo_states', action=OverrideDefaultListAction,
                           type=int, default=tempo_states,
                           help='possible tempo states (multiple values can '
                                'be given)')
        if correct:
            g.add_argument('--no_correct', dest='correct',
                           action='store_false', default=correct,
                           help='do not correct the beat positions')
        else:
            g.add_argument('--correct', dest='correct',
                           action='store_true', default=correct,
                           help='correct the beat positions')
        if norm_observations:
            g.add_argument('--no_norm_obs', dest='norm_observations',
                           action='store_false', default=norm_observations,
                           help='do not normalise the observations of the DBN')
        else:
            g.add_argument('--norm_obs', dest='norm_observations',
                           action='store_true', default=norm_observations,
                           help='normalise the observations of the DBN')
        # return the argument group so it can be modified if needed
        return g
