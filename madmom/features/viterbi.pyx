# encoding: utf-8
"""
This file contains the speed crucial conditional random field related
functionality.

@author: Filip Korzeniowski <filip.korzeniowski@jku.at>

"""

import numpy as np
cimport numpy as np
cimport cython
from libc.math cimport log


@cython.cdivision(True)
@cython.boundscheck(False)
@cython.wraparound(False)
def crf_viterbi(np.ndarray[np.float32_t, ndim=1] pi,
                np.ndarray[np.float32_t, ndim=1] transition,
                np.ndarray[np.float32_t, ndim=1] norm_factor,
                np.ndarray[np.float32_t, ndim=1] activations,
                int tau):
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

    # back-tracking pointer sequence
    cdef list bps = []
    # current viterbi variables
    cdef np.ndarray[np.float32_t, ndim=1] v_c = np.zeros(num_st, dtype=np.float32)
    # previous viterbi variables
    cdef np.ndarray[np.float32_t, ndim=1] v_p = np.zeros(num_st, dtype=np.float32)
    # current back-tracking pointers; init them with -1
    cdef np.ndarray[np.int_t, ndim=1] bp_c = np.ones_like(v_c, dtype=int) * -1
    # back tracked path, a.k.a. path sequence
    cdef list path = []

    # counters etc.
    cdef int k, i, j, next_state
    cdef double cur, new, sum_k, log_sum = 0.0

    # init first beat
    v_p = pi * activations
    v_p /= v_p.sum()

    # iterate over all beats; the 1st beat is given by prior
    for k in range(num_x - 1):
        # reset all current viterbi variables
        for i in range(num_st):
            v_c[i] = 0.0
        # search the best transition
        for i in range(num_st):
            for j in range(num_tr):
                if (i + j) >= num_st:
                    break

                cur = v_c[i + j]
                new = v_p[i] * transition[j] * activations[i + j] * norm_factor[i]

                if new > cur:
                    v_c[i + j] = new
                    bp_c[i + j] = i

        sum_k = 0.0
        for i in range(num_st):
            sum_k += v_c[i]

        for i in range(num_st):
            v_c[i] /= sum_k

        log_sum += log(sum_k)

        v_p, v_c = v_c, v_p
        bps.append(bp_c.copy())

    # add the final best state to the path
    next_state = v_p.argmax()
    path.append(next_state)
    # track the path backwards
    for i in range(num_x - 2, -1, -1):
        next_state = bps[i][next_state]
        path.append(next_state)
    # return the best sequence and its log probability
    return np.array(path[::-1]), log(v_p.max()) + log_sum


def mm_viterbi(np.ndarray[np.float32_t, ndim=1] activations,
               int num_beat_cells=640,
               float tempo_change_probability=0.002,
               int beat_lambda=16,
               int min_bpm=40,
               int max_bpm=240):
    """
    Track the beats with a dynamic Bayesian network.

    :param num_beat_cells:           number of cells for one beat period
    :param num_tempo_states:         number of tempo states
    :param tempo_change_probability: probability of a tempo change from
                                     one observation to the next one
    :param beat_proportion:          proportion of beat to no-beat length
    :param min_bpm:                  minimum tempo used for beat tracking
    :param max_bpm:                  maximum tempo used for beat tracking
    :return:                         detected beat positions

    """
    # variables
    cdef int psi = 640  # number of beat states
    cdef int l = 16
    cdef double p = 0.002
    cdef int min_tempo = 5
    cdef int max_tempo = 23
    cdef int num_states = psi * max_tempo

    # back-tracking pointer sequence
    cdef list bps = []
    # current viterbi variables
    cdef np.ndarray[np.float32_t, ndim=1] current_viterbi = \
        np.zeros(num_states, dtype=np.float32)
    # previous viterbi variables
    cdef np.ndarray[np.float32_t, ndim=1] prev_viterbi = \
        np.ones(num_states, dtype=np.float32)
    # current back-tracking pointers; init them with -1
    cdef np.ndarray[np.int_t, ndim=1] current_pointers = \
        np.ones_like(current_viterbi, dtype=int) * -1
    # back tracked path, a.k.a. path sequence
    cdef list path = []

    # counters etc.
    cdef int state, pib, tempo, prev, next_state
    cdef double act, obs, cur

    # iterate over all observations
    for act in activations:
        # reset all current viterbi variables
        current_viterbi[:] = 0.0
        # search for best transitions
        for state in range(num_states):
            # position inside beat & tempo
            pib = state % psi
            tempo = state / psi
            # get the observation
            if pib < psi / l:
                obs = act
            else:
                obs = (1. - act) / (l - 1)
            # for each state check the 3 possible transitions
            # transition from same tempo
            prev = (pib - tempo) % psi + (tempo * psi)
            cur = prev_viterbi[prev] * (1. - p) * obs
            if cur > current_viterbi[state]:
                current_viterbi[state] = cur
                current_pointers[state] = prev
            # transition from slower tempo
            if tempo > min_tempo:
                prev = (pib - (tempo - 1)) % psi + ((tempo - 1) * psi)
                cur = prev_viterbi[prev] * 0.5 * p * obs
                # print prev, slower,
                if cur > current_viterbi[state]:
                    current_viterbi[state] = cur
                    current_pointers[state] = prev
            # transition from faster tempo
            if tempo < max_tempo - 1:
                prev = (pib - (tempo + 1)) % psi + ((tempo + 1) * psi)
                cur = prev_viterbi[prev] * 0.5 * p * obs
                # print prev, faster
                if cur > current_viterbi[state]:
                    current_viterbi[state] = cur
                    current_pointers[state] = prev
        # append current pointers to the back-tracking pointer sequence list
        bps.append(current_pointers.copy())
        # overwrite the old states with the normalised current ones
        prev_viterbi = current_viterbi / current_viterbi.max()

    # add the final best state to the path
    next_state = current_viterbi.argmax()
    path.append(next_state)

    # track the path backwards
    for i in range(1, len(bps)):
        next_state = bps[-i][next_state]
        path.append(next_state)

    # return
    return np.array(path[::-1])
