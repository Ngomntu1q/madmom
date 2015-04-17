# encoding: utf-8
"""
This file contains tests for the madmom.evaluation.beats module.

@author: Sebastian Böck <sebastian.boeck@jku.at>

"""
# pylint: skip-file

import unittest

from madmom.evaluation.beats import *
from madmom.evaluation.beats import (_histogram_bins, _error_histogram,
                                     _information_gain, _entropy)

ANNOTATIONS = np.asarray([1., 2, 3, 4, 5, 6, 7, 8, 9, 10])
OFFBEAT_ANNOTATIONS = np.asarray([1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5])
DOUBLE_ANNOTATIONS = np.asarray([1., 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6,
                                 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10])
TRIPLE_ANNOTATIONS = np.asarray([1, 1.333333, 1.666667, 2, 2.333333, 2.666667,
                                 3, 3.333333, 3.666667, 4, 4.333333, 4.666667,
                                 5, 5.333333, 5.666667, 6, 6.333333, 6.666667,
                                 7, 7.333333, 7.666667, 8, 8.333333, 8.666667,
                                 9, 9.333333, 9.666667, 10])
DETECTIONS = np.asarray([1.01, 2, 2.95, 4, 6, 7, 8, 9.1, 10, 11])


# test functions
class TestVariationsFunction(unittest.TestCase):

    def test_types(self):
        sequences = variations(ANNOTATIONS)
        self.assertIsInstance(sequences, list)

    def test_values(self):
        # no variations
        sequences = variations(ANNOTATIONS)
        self.assertTrue(len(sequences) == 0)
        self.assertEqual(sequences, [])
        # offbeat
        self.assertTrue(len(sequences) == 0)
        sequences = variations(ANNOTATIONS, offbeat=True)
        self.assertTrue(len(sequences) == 1)
        self.assertTrue(np.allclose(sequences[0], OFFBEAT_ANNOTATIONS))
        # double
        sequences = variations(ANNOTATIONS, double=True)
        self.assertTrue(len(sequences) == 1)
        self.assertTrue(np.allclose(sequences[0], DOUBLE_ANNOTATIONS))
        # half tempo (includes starting with 1st or 2nd beat)
        sequences = variations(ANNOTATIONS, half=True)
        self.assertTrue(len(sequences) == 2)
        self.assertTrue(np.allclose(sequences[0], ANNOTATIONS[0::2]))
        self.assertTrue(np.allclose(sequences[1], ANNOTATIONS[1::2]))
        # triple
        sequences = variations(ANNOTATIONS, triple=True)
        self.assertTrue(len(sequences) == 1)
        self.assertTrue(np.allclose(sequences[0], TRIPLE_ANNOTATIONS))
        # third (includes starting with 1st, 2nd or 3rd beat)
        sequences = variations(ANNOTATIONS, third=True)
        self.assertTrue(len(sequences) == 3)
        self.assertTrue(np.allclose(sequences[0], ANNOTATIONS[0::3]))
        self.assertTrue(np.allclose(sequences[1], ANNOTATIONS[1::3]))
        self.assertTrue(np.allclose(sequences[2], ANNOTATIONS[2::3]))


class TestCalcIntervalFunction(unittest.TestCase):

    def test_types(self):
        intervals = calc_intervals(ANNOTATIONS)
        self.assertIsInstance(intervals, np.ndarray)
        # events must be correct type
        intervals = calc_intervals([1, 2])
        self.assertIsInstance(intervals, np.ndarray)

    def test_errors(self):
        # empty or length 1 sequences should raise an error
        with self.assertRaises(BeatIntervalError):
            calc_intervals([])
        with self.assertRaises(BeatIntervalError):
            calc_intervals([1])

    def test_values(self):
        # test annotations backwards
        intervals = calc_intervals(ANNOTATIONS)
        correct = np.asarray([1., 1, 1, 1, 1, 1, 1, 1, 1, 1])
        self.assertTrue(np.allclose(intervals, correct))
        # test detections backwards
        intervals = calc_intervals(DETECTIONS)
        correct = [0.99, 0.99, 0.95, 1.05, 2, 1, 1, 1.1, 0.9, 1]
        self.assertTrue(np.allclose(intervals, correct))
        # test annotations forwards
        intervals = calc_intervals(ANNOTATIONS, fwd=True)
        correct = np.asarray([1., 1, 1, 1, 1, 1, 1, 1, 1, 1])
        self.assertTrue(np.allclose(intervals, correct))
        # test detections forwards
        intervals = calc_intervals(DETECTIONS, fwd=True)
        correct = [0.99, 0.95, 1.05, 2, 1, 1, 1.1, 0.9, 1, 1]
        self.assertTrue(np.allclose(intervals, correct))
        # TODO: same tests with matches given


class TestFindClosestIntervalFunction(unittest.TestCase):

    def test_types(self):
        intervals = find_closest_intervals(DETECTIONS, ANNOTATIONS)
        self.assertIsInstance(intervals, np.ndarray)
        # events must be correct type
        with self.assertRaises(TypeError):
            find_closest_intervals(None, ANNOTATIONS)
        with self.assertRaises(TypeError):
            find_closest_intervals(DETECTIONS, None)

    def test_errors(self):
        # less than 2 annotations should raise an error
        with self.assertRaises(BeatIntervalError):
            find_closest_intervals(DETECTIONS, [])
        with self.assertRaises(BeatIntervalError):
            find_closest_intervals(DETECTIONS, [1.])

    def test_values(self):
        # empty detections should return an empty result
        intervals = find_closest_intervals([], ANNOTATIONS)
        self.assertTrue(np.allclose(intervals, []))
        # test detections w.r.t. annotations
        intervals = find_closest_intervals(DETECTIONS, ANNOTATIONS)
        correct = np.asarray([1., 1, 1, 1, 1, 1, 1, 1, 1, 1])
        self.assertTrue(np.allclose(intervals, correct))
        # intervals = find_closest_intervals(DETECTIONS, EVENTS)
        # correct = np.asarray([1., 1, 1, 1, 1, 1, 1, 1, 1, 1])
        # test annotations w.r.t. detections
        intervals = find_closest_intervals(ANNOTATIONS, DETECTIONS)
        correct = [0.99, 0.99, 1.05, 1.05, 2, 2, 1, 1, 1.1, 0.9]
        self.assertTrue(np.allclose(intervals, correct))
        # TODO: same tests with matches given


class TestFindLongestContinuousSegmentFunction(unittest.TestCase):

    def test_types(self):
        length, start = find_longest_continuous_segment(np.asarray([]))
        self.assertIsInstance(length, int)
        self.assertIsInstance(start, int)
        length, start = find_longest_continuous_segment([])
        self.assertIsInstance(length, int)
        self.assertIsInstance(start, int)
        # events must be correct type
        with self.assertRaises(IndexError):
            find_longest_continuous_segment(None)
        with self.assertRaises(IndexError):
            find_longest_continuous_segment(1)

    def test_values(self):
        length, start = find_longest_continuous_segment([])
        self.assertEqual(length, 0)
        self.assertEqual(start, 0)
        length, start = find_longest_continuous_segment([5])
        self.assertEqual(length, 1)
        self.assertEqual(start, 0)
        #
        length, start = find_longest_continuous_segment([0, 1, 2, 3])
        self.assertEqual(length, 4)
        self.assertEqual(start, 0)
        length, start = find_longest_continuous_segment([0, 2, 3, 5, 6, 7, 9])
        self.assertEqual(length, 3)
        self.assertEqual(start, 3)


class TestCalcRelativeErrorsFunction(unittest.TestCase):

    def test_types(self):
        rel_errors = calc_relative_errors(DETECTIONS, ANNOTATIONS)
        self.assertIsInstance(rel_errors, np.ndarray)
        # events must be correct type
        with self.assertRaises(TypeError):
            calc_relative_errors(None, ANNOTATIONS)
        with self.assertRaises(TypeError):
            calc_relative_errors(DETECTIONS, None)

    def test_errors(self):
        # less than 2 annotations should raise an error
        with self.assertRaises(BeatIntervalError):
            calc_relative_errors(DETECTIONS, [])
        with self.assertRaises(BeatIntervalError):
            calc_relative_errors(DETECTIONS, [1.])

    def test_values(self):
        # empty detections should return an empty result
        errors = calc_relative_errors([], ANNOTATIONS)
        self.assertTrue(np.allclose(errors, []))
        # test detections w.r.t. annotations
        errors = calc_relative_errors(DETECTIONS, ANNOTATIONS)
        # det: [1.01, 2, 2.95, 4,    6, 7, 8, 9.1, 10, 11]
        # tar: [1,    2, 3,    4, 5, 6, 7, 8, 9,   10]
        correct = [0.01, 0, -0.05, 0, 0, 0, 0, 0.1, 0, 1]
        # all intervals are 1, so need for division
        self.assertTrue(np.allclose(errors, correct))
        # test annotations w.r.t. detections
        errors = calc_relative_errors(ANNOTATIONS, DETECTIONS)
        # tar: [1,    2, 3,    4, 5, 6, 7, 8, 9,   10]
        # det: [1.01, 2, 2.95, 4,    6, 7, 8, 9.1, 10, 11]
        errors_ = np.asarray([-0.01, 0, 0.05, 0, -1, 0, 0, 0, -0.1, 0])
        intervals_ = np.asarray([0.99, 0.99, 1.05, 1.05, 2, 2, 1, 1, 1.1, 0.9])
        self.assertTrue(np.allclose(errors, errors_ / intervals_))
        # TODO: same tests with matches given


class TestPscoreFunction(unittest.TestCase):

    def test_types(self):
        score = pscore(DETECTIONS, ANNOTATIONS, 0.2)
        self.assertIsInstance(score, float)
        # detections / annotations must be correct type
        score = pscore([], [], 0.2)
        self.assertIsInstance(score, float)
        score = pscore({}, {}, 0.2)
        self.assertIsInstance(score, float)
        with self.assertRaises(TypeError):
            pscore(None, ANNOTATIONS, 0.2)
        with self.assertRaises(TypeError):
            pscore(DETECTIONS, None, 0.2)
        # tolerance must be correct type
        score = pscore(DETECTIONS, ANNOTATIONS, int(1.2))
        self.assertIsInstance(score, float)
        with self.assertRaises(ValueError):
            pscore(DETECTIONS, ANNOTATIONS, [])
        with self.assertRaises(TypeError):
            pscore(DETECTIONS, ANNOTATIONS, {})

    def test_errors(self):
        # tolerance must be > 0
        with self.assertRaises(ValueError):
            pscore(DETECTIONS, ANNOTATIONS, 0)
        with self.assertRaises(ValueError):
            pscore(DETECTIONS, ANNOTATIONS, None)
        # score relies on intervals, hence at least 2 annotations must be given
        with self.assertRaises(BeatIntervalError):
            pscore(DETECTIONS, [1], 0.2)

    def test_values(self):
        # two empty sequences should have a perfect score
        score = pscore([], [], 0.2)
        self.assertEqual(score, 1)
        # if we have no annotations but detections, the score should be 0
        score = pscore(DETECTIONS, [], 0.2)
        self.assertEqual(score, 0)
        # no detections should return 0
        score = pscore([], ANNOTATIONS, 0.2)
        self.assertEqual(score, 0)
        # normal calculation
        score = pscore(DETECTIONS, ANNOTATIONS, 0.2)
        self.assertEqual(score, 0.9)


class TestCemgilFunction(unittest.TestCase):

    def test_types(self):
        score = cemgil(DETECTIONS, ANNOTATIONS, 0.04)
        self.assertIsInstance(score, float)
        # detections / annotations must be correct type
        score = cemgil([], [], 0.04)
        self.assertIsInstance(score, float)
        score = cemgil({}, {}, 0.04)
        self.assertIsInstance(score, float)
        with self.assertRaises(TypeError):
            cemgil(None, ANNOTATIONS, 0.04)
        with self.assertRaises(TypeError):
            cemgil(DETECTIONS, None, 0.04)
        # tolerance must be correct type
        score = cemgil(DETECTIONS, ANNOTATIONS, int(1))
        self.assertIsInstance(score, float)
        with self.assertRaises(TypeError):
            cemgil(DETECTIONS, ANNOTATIONS, [0.04])
        with self.assertRaises(TypeError):
            cemgil(DETECTIONS, ANNOTATIONS, {0: 0.04})
        with self.assertRaises(TypeError):
            cemgil(DETECTIONS, ANNOTATIONS, {0.04: 0})

    def test_errors(self):
        # sigma must be greater than 0
        with self.assertRaises(ValueError):
            cemgil(DETECTIONS, ANNOTATIONS, 0)
        with self.assertRaises(ValueError):
            cemgil(DETECTIONS, ANNOTATIONS, None)

    def test_values(self):
        # two empty sequences should have a perfect score
        score = cemgil([], [], 0.04)
        self.assertEqual(score, 1)
        # if we have no annotations but detections, the score should be 0
        score = cemgil(DETECTIONS, [], 0.04)
        self.assertEqual(score, 0)
        # score doesn't use intervals, thus don't check number of annotations
        # no detections should return 0
        score = cemgil([], ANNOTATIONS, 0.04)
        self.assertEqual(score, 0)
        # normal calculation
        score = cemgil(DETECTIONS, ANNOTATIONS, 0.04)
        self.assertEqual(score, 0.74710035298713695)


class TestGotoFunction(unittest.TestCase):

    def test_types(self):
        score = goto(DETECTIONS, ANNOTATIONS, 0.175, 0.2, 0.2)
        self.assertIsInstance(score, float)
        # detections / annotations must be correct type
        score = goto([], [], 0.175, 0.2, 0.2)
        self.assertIsInstance(score, float)
        score = goto({}, {}, 0.175, 0.2, 0.2)
        self.assertIsInstance(score, float)
        with self.assertRaises(TypeError):
            goto(None, ANNOTATIONS, 0.175, 0.2, 0.2)
        with self.assertRaises(TypeError):
            goto(DETECTIONS, None, 0.175, 0.2, 0.2)
        # parameters must be correct type
        score = goto(DETECTIONS, ANNOTATIONS, int(0.175), 0.2, 0.2)
        self.assertIsInstance(score, float)
        score = goto(DETECTIONS, ANNOTATIONS, 0.175, int(0.2), 0.2)
        self.assertIsInstance(score, float)
        score = goto(DETECTIONS, ANNOTATIONS, 0.175, 0.2, int(0.2))
        self.assertIsInstance(score, float)

    def test_errors(self):
        # parameters must not be None
        with self.assertRaises(ValueError):
            goto(DETECTIONS, ANNOTATIONS, None, 0.2, 0.2)
        with self.assertRaises(ValueError):
            goto(DETECTIONS, ANNOTATIONS, 0.175, None, 0.2)
        with self.assertRaises(ValueError):
            goto(DETECTIONS, ANNOTATIONS, 0.175, 0.2, None)
        # parameters must be positive
        with self.assertRaises(ValueError):
            goto(DETECTIONS, ANNOTATIONS, -1, 0.2, 0.2)
        with self.assertRaises(ValueError):
            goto(DETECTIONS, ANNOTATIONS, 0.175, -1, 0.2)
        with self.assertRaises(ValueError):
            goto(DETECTIONS, ANNOTATIONS, 0.175, 0.2, -1)
        # score relies on intervals, hence at least 2 annotations must be given
        with self.assertRaises(BeatIntervalError):
            goto(DETECTIONS, [1], 0.175, 0.2, 0.2)

    def test_values(self):
        # two empty sequences should have a perfect score
        score = goto([], [], 0.175, 0.2, 0.2)
        self.assertEqual(score, 1)
        # if we have no annotations but detections, the score should be 0
        score = goto(DETECTIONS, [], 0.175, 0.2, 0.2)
        self.assertEqual(score, 0)
        # no detections should return 0
        score = goto([], ANNOTATIONS, 0.175, 0.2, 0.2)
        self.assertEqual(score, 0)
        # normal calculation
        score = goto(DETECTIONS, ANNOTATIONS, 0.175, 0.2, 0.2)
        self.assertEqual(score, 1)
        # simple example where the Matlab implementation fails
        det = np.array([0, 0.5, 1, 1.5, 2, 5, 6, 7, 8, 9])
        ann = np.arange(10)
        self.assertEqual(goto(det, ann), 1)
        self.assertEqual(goto(ann, det), 1)


class TestCmlFunction(unittest.TestCase):

    def test_types(self):
        cmlc, cmlt = cml(DETECTIONS, ANNOTATIONS, 0.175, 0.175)
        self.assertIsInstance(cmlc, float)
        self.assertIsInstance(cmlt, float)
        # detections / annotations must be correct type
        cmlc, cmlt = cml([], [], 0.175, 0.175)
        self.assertIsInstance(cmlc, float)
        self.assertIsInstance(cmlt, float)
        cmlc, cmlt = cml({}, {}, 0.175, 0.175)
        self.assertIsInstance(cmlc, float)
        self.assertIsInstance(cmlt, float)
        with self.assertRaises(TypeError):
            cml(None, ANNOTATIONS, 0.175, 0.175)
        with self.assertRaises(TypeError):
            cml(DETECTIONS, None, 0.175, 0.175)
        # tolerances must be correct type
        cmlc, cmlt = cml(DETECTIONS, ANNOTATIONS, int(1), int(1))
        self.assertIsInstance(cmlc, float)
        self.assertIsInstance(cmlt, float)
        cmlc, cmlt = cml(DETECTIONS, ANNOTATIONS, [0.175], [0.175])
        self.assertIsInstance(cmlc, float)
        self.assertIsInstance(cmlt, float)
        with self.assertRaises(TypeError):
            cml(DETECTIONS, ANNOTATIONS, {}, {})

    def test_errors(self):
        # tolerances must be greater than 0
        with self.assertRaises(ValueError):
            cml(DETECTIONS, ANNOTATIONS, 0, None)
        with self.assertRaises(ValueError):
            cml(DETECTIONS, ANNOTATIONS, None, 0)
        # score relies on intervals, hence at least 2 annotations must be given
        with self.assertRaises(BeatIntervalError):
            cml(DETECTIONS, [1.], 0.175, 0.175)

    def test_values(self):
        # two empty sequences should have a perfect score
        scores = cml([], [], 0.175, 0.175)
        self.assertEqual(scores, (1, 1))
        # if we have no annotations but detections, the score should be 0
        scores = cml(DETECTIONS, [], 0.175, 0.175)
        self.assertEqual(scores, (0, 0))
        # no detections should return 0
        scores = cml([], ANNOTATIONS, 0.175, 0.175)
        self.assertEqual(scores, (0, 0))
        # normal calculation
        scores = cml(DETECTIONS, ANNOTATIONS, 0.175, 0.175)
        self.assertEqual(scores, (0.4, 0.8))


class TestContinuityFunction(unittest.TestCase):

    def test_types(self):
        cmlc, cmlt, amlc, amlt = continuity(DETECTIONS, ANNOTATIONS,
                                            0.175, 0.175)
        self.assertIsInstance(cmlc, float)
        self.assertIsInstance(cmlt, float)
        self.assertIsInstance(amlc, float)
        self.assertIsInstance(amlt, float)
        # detections / annotations must be correct type
        cmlc, cmlt, amlc, amlt = continuity([], [], 0.175, 0.175)
        self.assertIsInstance(cmlc, float)
        self.assertIsInstance(cmlt, float)
        self.assertIsInstance(amlc, float)
        self.assertIsInstance(amlt, float)
        cmlc, cmlt, amlc, amlt = continuity({}, {}, 0.175, 0.175)
        self.assertIsInstance(cmlc, float)
        self.assertIsInstance(cmlt, float)
        self.assertIsInstance(amlc, float)
        self.assertIsInstance(amlt, float)
        with self.assertRaises(TypeError):
            continuity(None, ANNOTATIONS, 0.175, 0.175)
        with self.assertRaises(TypeError):
            continuity(DETECTIONS, None, 0.175, 0.175)
        # tolerances must be correct type
        scores = continuity(DETECTIONS, ANNOTATIONS, int(1), int(1))
        cmlc, cmlt, amlc, amlt = scores
        self.assertIsInstance(cmlc, float)
        self.assertIsInstance(cmlt, float)
        self.assertIsInstance(amlc, float)
        self.assertIsInstance(amlt, float)
        scores = continuity(DETECTIONS, ANNOTATIONS, [0.175], [0.175])
        cmlc, cmlt, amlc, amlt = scores
        self.assertIsInstance(cmlc, float)
        self.assertIsInstance(cmlt, float)
        self.assertIsInstance(amlc, float)
        self.assertIsInstance(amlt, float)
        with self.assertRaises(TypeError):
            continuity(DETECTIONS, ANNOTATIONS, {}, {})

    def test_errors(self):
        # tolerances must be greater than 0
        with self.assertRaises(ValueError):
            continuity(DETECTIONS, ANNOTATIONS, 0, None)
        with self.assertRaises(ValueError):
            continuity(DETECTIONS, ANNOTATIONS, None, 0)
        # score relies on intervals, hence at least 2 annotations must be given
        with self.assertRaises(BeatIntervalError):
            continuity(DETECTIONS, [1.], 0.175, 0.175)

    def test_values(self):
        # two empty sequences should have a perfect score
        scores = continuity([], [], 0.175, 0.175)
        self.assertEqual(scores, (1, 1, 1, 1))
        # if we have no annotations but detections, the score should be 0
        scores = continuity(DETECTIONS, [], 0.175, 0.175)
        self.assertEqual(scores, (0, 0, 0, 0))
        # no detections should return 0
        scores = continuity([], ANNOTATIONS, 0.175, 0.175)
        self.assertEqual(scores, (0, 0, 0, 0))
        # normal calculation
        scores = continuity(DETECTIONS, ANNOTATIONS, 0.175, 0.175)
        self.assertEqual(scores, (0.4, 0.8, 0.4, 0.8))
        # double tempo annotations
        scores = continuity(DETECTIONS, DOUBLE_ANNOTATIONS, 0.175, 0.175)
        self.assertEqual(scores, (0., 0., 0.4, 0.8))
        scores = continuity(DETECTIONS, DOUBLE_ANNOTATIONS, 0.175, 0.175,
                            double=False, triple=False)
        self.assertEqual(scores, (0., 0., 0., 0.))
        scores = continuity(DETECTIONS, DOUBLE_ANNOTATIONS, 0.175, 0.175,
                            double=True, triple=False)
        self.assertEqual(scores, (0., 0., 0.4, 0.8))
        scores = continuity(DETECTIONS, DOUBLE_ANNOTATIONS, 0.175, 0.175,
                            double=False, triple=True)
        self.assertEqual(scores, (0., 0., 0., 0.))
        # half tempo annotations (even beats)
        scores = continuity(DETECTIONS, ANNOTATIONS[::2], 0.175, 0.175)
        self.assertEqual(scores, (0., 0., 0.4, 0.7))
        scores = continuity(DETECTIONS, ANNOTATIONS[::2], 0.175, 0.175,
                            double=False, triple=False)
        self.assertEqual(scores, (0., 0., 0.1, 0.1))
        scores = continuity(DETECTIONS, ANNOTATIONS[::2], 0.175, 0.175,
                            double=True, triple=False)
        self.assertEqual(scores, (0., 0., 0.4, 0.7))
        scores = continuity(DETECTIONS, ANNOTATIONS[::2], 0.175, 0.175,
                            double=False, triple=True)
        self.assertEqual(scores, (0., 0., 0.1, 0.1))
        # half tempo annotations (odd beats)
        scores = continuity(DETECTIONS, ANNOTATIONS[1::2], 0.175, 0.175)
        self.assertEqual(scores, (0.1, 0.1, 0.4, 0.7))
        scores = continuity(DETECTIONS, ANNOTATIONS[1::2], 0.175, 0.175,
                            double=False, triple=False)
        self.assertEqual(scores, (0.1, 0.1, 0.1, 0.1))
        scores = continuity(DETECTIONS, ANNOTATIONS[1::2], 0.175, 0.175,
                            double=True, triple=False)
        self.assertEqual(scores, (0.1, 0.1, 0.4, 0.7))
        scores = continuity(DETECTIONS, ANNOTATIONS[1::2], 0.175, 0.175,
                            double=False, triple=True)
        self.assertEqual(scores, (0.1, 0.1, 0.1, 0.1))
        # triple tempo annotations
        scores = continuity(DETECTIONS, TRIPLE_ANNOTATIONS, 0.175, 0.175)
        self.assertEqual(scores, (0., 0., 0.4, 0.8))
        scores = continuity(DETECTIONS, TRIPLE_ANNOTATIONS, 0.175, 0.175,
                            double=False, triple=False)
        self.assertEqual(scores, (0., 0., 0., 0.))
        scores = continuity(DETECTIONS, TRIPLE_ANNOTATIONS, 0.175, 0.175,
                            double=True, triple=False)
        self.assertEqual(scores, (0., 0., 0., 0.))
        scores = continuity(DETECTIONS, TRIPLE_ANNOTATIONS, 0.175, 0.175,
                            double=False, triple=True)
        self.assertEqual(scores, (0., 0., 0.4, 0.8))
        # third tempo annotations (starting with 1st beat)
        scores = continuity(DETECTIONS, ANNOTATIONS[::3], 0.175, 0.175)
        self.assertEqual(scores, (0., 0., 0.4, 0.8))
        scores = continuity(DETECTIONS, ANNOTATIONS[::3], 0.175, 0.175,
                            double=False, triple=False)
        self.assertEqual(scores, (0., 0., 0., 0.))
        scores = continuity(DETECTIONS, ANNOTATIONS[::3], 0.175, 0.175,
                            double=True, triple=False)
        self.assertEqual(scores, (0., 0., 0., 0.))
        scores = continuity(DETECTIONS, ANNOTATIONS[::3], 0.175, 0.175,
                            double=False, triple=True)
        self.assertEqual(scores, (0., 0., 0.4, 0.8))
        # third tempo annotations (starting with 2nd beat)
        scores = continuity(DETECTIONS, ANNOTATIONS[1::3], 0.175, 0.175)
        self.assertEqual(scores, (0., 0., 0.3, 0.5))
        scores = continuity(DETECTIONS, ANNOTATIONS[1::3], 0.175, 0.175,
                            double=False, triple=False)
        self.assertEqual(scores, (0., 0., 0., 0.))
        scores = continuity(DETECTIONS, ANNOTATIONS[1::3], 0.175, 0.175,
                            double=True, triple=False)
        self.assertEqual(scores, (0., 0., 0., 0.))
        scores = continuity(DETECTIONS, ANNOTATIONS[1::3], 0.175, 0.175,
                            double=False, triple=True)
        self.assertEqual(scores, (0., 0., 0.3, 0.5))
        # third tempo annotations (starting with 3rd beat)
        scores = continuity(DETECTIONS, ANNOTATIONS[2::3], 0.175, 0.175)
        self.assertEqual(scores, (0., 0., 0.3, 0.5))
        scores = continuity(DETECTIONS, ANNOTATIONS[2::3], 0.175, 0.175,
                            double=False, triple=False)
        self.assertEqual(scores, (0., 0., 0., 0.))
        scores = continuity(DETECTIONS, ANNOTATIONS[2::3], 0.175, 0.175,
                            double=True, triple=False)
        self.assertEqual(scores, (0., 0., 0., 0.))
        scores = continuity(DETECTIONS, ANNOTATIONS[2::3], 0.175, 0.175,
                            double=False, triple=True)
        self.assertEqual(scores, (0., 0., 0.3, 0.5))


class TestHistogramBinsHelperFunction(unittest.TestCase):

    def test_types(self):
        bins = _histogram_bins(40)
        self.assertIsInstance(bins, np.ndarray)
        self.assertTrue(bins.dtype == np.float)

    def test_errors(self):
        # bins must be even and greater or equal than 2
        with self.assertRaises(ValueError):
            _histogram_bins(1)
        with self.assertRaises(ValueError):
            _histogram_bins(2.1)
        with self.assertRaises(ValueError):
            _histogram_bins(5)

    def test_values(self):
        # test some well defined situations
        bins = _histogram_bins(2)
        # the bins must be 0.5 wide and centered around 0
        self.assertTrue(np.allclose(bins, [-0.75, -0.25, 0.25, 0.75]))
        bins = _histogram_bins(4)
        # the bins must be 0.25 wide and centered around 0
        self.assertTrue(np.allclose(bins, [-0.625, -0.375, -0.125, 0.125,
                                           0.375, 0.625]))


class TestErrorHistogramHelperFunction(unittest.TestCase):

    def test_types(self):
        bins = _histogram_bins(4)
        hist = _error_histogram(DETECTIONS, ANNOTATIONS, bins)
        self.assertIsInstance(hist, np.ndarray)
        self.assertTrue(hist.dtype == np.float)

    def test_values(self):
        # first bin maps the ±0.5 interval error, the second the 0
        bins = _histogram_bins(2)
        ann = np.asarray([0, 1, 2, 3])
        # A) identical detections map to the 0 error bin
        hist = _error_histogram(np.asarray([0, 1, 2, 3]), ann, bins)
        self.assertTrue(np.allclose(hist, [0, 4]))
        # bins maps the ±0.5, -0.25, 0, 0.25 interval errors
        bins = _histogram_bins(4)
        # B) identical detections map to the 0 error bin
        hist = _error_histogram(ann, ann, bins)
        self.assertTrue(np.allclose(hist, [0, 0, 4, 0]))
        # C) offbeat detections map to the ±0.5 error bin
        hist = _error_histogram(np.asarray([0.5, 1.5, 2.5, 3.5]), ann, bins)
        self.assertTrue(np.allclose(hist, [4, 0, 0, 0]))
        # D) smaller deviations mapping to the 0 and 0.125 error bins
        hist = _error_histogram(np.asarray([0.125, 0.875, 2.1, 3]), ann, bins)
        self.assertTrue(np.allclose(hist, [0, 0, 3, 1]))
        # E) default annotations and detections with 40 bins
        bins = _histogram_bins(40)
        hist = _error_histogram(DETECTIONS, ANNOTATIONS, bins)
        self.assertTrue(np.allclose(hist, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                           0, 0, 0, 0, 0, 0, 1, 0, 8, 0, 0, 0,
                                           1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                           0, 0, 0, 0]))


class TestEntropyHelperFunction(unittest.TestCase):

    def test_types(self):
        entropy = _entropy(np.ones(6))
        self.assertIsInstance(entropy, float)

    def test_values(self):
        # uniform histogram
        self.assertTrue(_entropy([1, 1, 1]) == np.log2(3))
        # use the examples of the TestErrorHistogramHelperFunction test above
        # A)
        hist = [0, 4]
        self.assertTrue(_entropy(hist) == 0)
        # B)
        hist = [0, 0, 4, 0]
        self.assertTrue(_entropy(hist) == 0)
        # C)
        hist = [4, 0, 0, 0]
        self.assertTrue(_entropy(hist) == 0)
        # D)
        hist = [0, 0, 3, 1]
        self.assertTrue(np.allclose(_entropy(hist), 0.811278124459))
        # E)
        hist = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0,
                8, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.assertTrue(np.allclose(_entropy(hist), 0.921928094887))


class TestInformationGainHelperFunction(unittest.TestCase):

    def test_types(self):
        bins = _histogram_bins(4)
        hist = _error_histogram(DETECTIONS, ANNOTATIONS, bins)
        ig = _information_gain(hist)
        self.assertIsInstance(ig, float)

    def test_values(self):
        # information gain is np.log2(len(histogram)) - entropy(histogram)
        # histogram with zeros
        self.assertTrue(_information_gain([0, 0, 0]) == np.log2(3))
        # uniform histogram
        self.assertTrue(_information_gain([1, 1, 1]) == 0)
        # use the examples of the TestErrorHistogramHelperFunction test above
        # A)
        hist = [0, 4]
        self.assertTrue(_information_gain(hist) == np.log2(2))
        # B)
        hist = [0, 0, 4, 0]
        self.assertTrue(_information_gain(hist) == np.log2(4))
        # C)
        hist = [4, 0, 0, 0]
        self.assertTrue(_information_gain(hist) == np.log2(4))
        # D)
        hist = [0, 0, 3, 1]
        self.assertTrue(np.allclose(_information_gain(hist), 1.18872187554))
        # E)
        hist = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0,
                8, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.assertTrue(_information_gain(hist) == 4.4)


class TestInformationGainFunction(unittest.TestCase):

    def test_types(self):
        ig, histogram = information_gain(DETECTIONS, ANNOTATIONS, 40)
        self.assertIsInstance(ig, float)
        self.assertIsInstance(histogram, np.ndarray)
        # detections / annotations must be correct type
        ig, histogram = information_gain([], [], 40)
        self.assertIsInstance(ig, float)
        self.assertIsInstance(histogram, np.ndarray)
        ig, histogram = information_gain({}, {}, 40)
        self.assertIsInstance(ig, float)
        self.assertIsInstance(histogram, np.ndarray)
        with self.assertRaises(TypeError):
            information_gain(None, ANNOTATIONS, 40)
        with self.assertRaises(TypeError):
            information_gain(DETECTIONS, None, 40)
        # tolerances must be correct type
        ig, histogram = information_gain(DETECTIONS, ANNOTATIONS, 40)
        self.assertIsInstance(ig, float)
        self.assertIsInstance(histogram, np.ndarray)
        ig, histogram = information_gain(DETECTIONS, ANNOTATIONS, 40)
        self.assertIsInstance(ig, float)
        self.assertIsInstance(histogram, np.ndarray)

    def test_errors(self):
        # score relies on intervals, hence at least 2 annotations must be given
        with self.assertRaises(BeatIntervalError):
            information_gain([1.], ANNOTATIONS, 4)
        with self.assertRaises(BeatIntervalError):
            information_gain(DETECTIONS, [1.], 4)

    def test_values(self):
        # empty sequences should return max score and a zero histogram
        ig, histogram = information_gain([], [], 4)
        self.assertEqual(ig, np.log2(4))
        self.assertTrue(np.allclose(histogram, np.zeros(4)))
        # if any of detections or annotations are empty, a score of 0 and a
        # uniform histogram should be returned
        uniform = np.ones(4) * 10. / 4
        ig, histogram = information_gain([], ANNOTATIONS, 4)
        self.assertEqual(ig, 0)
        self.assertTrue(np.allclose(histogram, uniform))
        ig, histogram = information_gain(DETECTIONS, [], 4)
        self.assertEqual(ig, 0)
        self.assertTrue(np.allclose(histogram, uniform))
        # normal calculation
        ig, histogram = information_gain(DETECTIONS, ANNOTATIONS, 4)
        # tar: [1,    2, 3,    4, 5, 6, 7, 8, 9,   10]
        # det: [1.01, 2, 2.95, 4,    6, 7, 8, 9.1, 10, 11]
        # errors: [-0.01, 0, 0.05, 0, -1, 0, 0, 0, -0.1, 0]
        # intervals: [0.99, 0.99, 1.05, 1.05, 2, 2, 1, 1, 1.1, 0.9]
        # rel. err.: [-0.01010101, 0, 0.04761905, 0, -0.5, 0, 0, 0,
        #             -0.09090909, 0]
        # bin edges: [-0.625 -0.375 -0.125  0.125  0.375  0.625]
        # bin count: [1, 0, 9, 0]
        # normalized histogram: [0.1, 0, 0.9, 0]
        # well-behaving histogram: [0.1, 1, 0.9, 1]
        # np.log2 histogram: [-3.32192809, 0, -0.15200309, 0]
        # entropy: 0.46899559358928122
        self.assertTrue(np.allclose(histogram, [1, 0, 9, 0]))
        self.assertEqual(ig, np.log2(4) - 0.46899559358928122)


# test evaluation class
class TestBeatEvaluationClass(unittest.TestCase):

    def test_types(self):
        e = BeatEvaluation(DETECTIONS, ANNOTATIONS)
        # from OnsetEvaluation
        self.assertIsInstance(e.num_tp, int)
        self.assertIsInstance(e.num_fp, int)
        self.assertIsInstance(e.num_tn, int)
        self.assertIsInstance(e.num_fn, int)
        self.assertIsInstance(e.precision, float)
        self.assertIsInstance(e.recall, float)
        self.assertIsInstance(e.fmeasure, float)
        self.assertIsInstance(e.accuracy, float)
        self.assertIsInstance(e.errors, list)
        self.assertIsInstance(e.mean_error, float)
        self.assertIsInstance(e.std_error, float)
        # additional beat score types
        self.assertIsInstance(e.pscore, float)
        self.assertIsInstance(e.cemgil, float)
        self.assertIsInstance(e.goto, float)
        self.assertIsInstance(e.cmlc, float)
        self.assertIsInstance(e.cmlt, float)
        self.assertIsInstance(e.amlc, float)
        self.assertIsInstance(e.amlt, float)
        self.assertIsInstance(e.information_gain, float)
        self.assertIsInstance(e.global_information_gain, float)
        self.assertIsInstance(e.error_histogram, np.ndarray)

    def test_conversion(self):
        # conversion from list should work
        e = BeatEvaluation([], [])
        self.assertIsInstance(e.tp, list)
        self.assertIsInstance(e.fp, list)
        self.assertIsInstance(e.tn, list)
        self.assertIsInstance(e.fn, list)
        # conversion from dict should work as well
        e = BeatEvaluation({}, {})
        self.assertIsInstance(e.tp, list)
        self.assertIsInstance(e.fp, list)
        self.assertIsInstance(e.tn, list)
        self.assertIsInstance(e.fn, list)
        # others should fail
        self.assertRaises(TypeError, BeatEvaluation, float(0), float(0))
        self.assertRaises(TypeError, BeatEvaluation, int(0), int(0))

    def test_results_empty(self):
        e = BeatEvaluation([], [])
        self.assertEqual(e.fmeasure, 1)
        self.assertEqual(e.pscore, 1)
        self.assertEqual(e.cemgil, 1)
        self.assertEqual(e.goto, 1)
        self.assertEqual(e.cmlc, 1)
        self.assertEqual(e.cmlt, 1)
        self.assertEqual(e.amlc, 1)
        self.assertEqual(e.amlt, 1)
        self.assertEqual(e.information_gain, np.log2(40))
        self.assertEqual(e.global_information_gain, np.log2(40))
        self.assertTrue(np.allclose(e.error_histogram, np.zeros(40)))

    def test_results(self):
        e = BeatEvaluation(DETECTIONS, ANNOTATIONS)
        # tar: [1,    2, 3,    4, 5, 6, 7, 8, 9,   10]
        # det: [1.01, 2, 2.95, 4,    6, 7, 8, 9.1, 10, 11]
        # WINDOW = 0.07
        # TOLERANCE = 0.2
        # SIGMA = 0.04
        # TEMPO_TOLERANCE = 0.175
        # PHASE_TOLERANCE = 0.175
        # BINS = 40
        self.assertEqual(e.tp, [1.01, 2, 2.95, 4, 6, 7, 8, 10])
        self.assertEqual(e.fp, [9.1, 11])
        self.assertEqual(e.tn, [])
        self.assertEqual(e.fn, [5, 9])
        self.assertEqual(e.num_tp, 8)
        self.assertEqual(e.num_fp, 2)
        self.assertEqual(e.num_tn, 0)
        self.assertEqual(e.num_fn, 2)
        self.assertEqual(e.precision, 8. / 10.)
        self.assertEqual(e.recall, 8. / 10.)
        f = 2 * (8. / 10.) * (8. / 10.) / ((8. / 10.) + (8. / 10.))
        self.assertEqual(e.fmeasure, f)
        self.assertEqual(e.accuracy, (8. + 0) / (8 + 2 + 0 + 2))
        # pscore: delta <= tolerance * median(inter beat interval)
        self.assertEqual(e.pscore, 9. / 10.)
        # cemgil:
        self.assertEqual(e.cemgil, 0.74710035298713695)
        self.assertEqual(e.goto, 1)
        self.assertEqual(e.cmlc, 0.4)
        self.assertEqual(e.cmlt, 0.8)
        self.assertEqual(e.amlc, 0.4)
        self.assertEqual(e.amlt, 0.8)
        self.assertEqual(e.information_gain, 3.965148445440323)
        self.assertEqual(e.global_information_gain, 3.965148445440323)
        error_histogram_ = np.zeros(40)
        error_histogram_[0] = 1
        error_histogram_[16] = 1
        error_histogram_[20] = 7
        error_histogram_[22] = 1
        self.assertTrue(np.allclose(e.error_histogram, error_histogram_))


class TestMeanBeatEvaluationClass(unittest.TestCase):

    def test_types(self):
        e = MeanBeatEvaluation()
        # scores
        self.assertIsInstance(e.fmeasure, float)
        self.assertIsInstance(e.pscore, float)
        self.assertIsInstance(e.cemgil, float)
        self.assertIsInstance(e.goto, float)
        self.assertIsInstance(e.cmlc, float)
        self.assertIsInstance(e.cmlt, float)
        self.assertIsInstance(e.amlc, float)
        self.assertIsInstance(e.amlt, float)
        self.assertIsInstance(e.information_gain, float)
        self.assertIsInstance(e.global_information_gain, float)
        # error histogram is initially None
        self.assertIsNone(e.error_histogram)

    def test_append(self):
        e = MeanBeatEvaluation()
        e.append(BeatEvaluation(DETECTIONS, ANNOTATIONS))
        self.assertIsInstance(e, MeanBeatEvaluation)
        # appending something valid should not return anything
        self.assertEqual(e.append(BeatEvaluation(DETECTIONS, ANNOTATIONS)),
                         None)
        # appending something else should not work

    def test_append_types(self):
        e = MeanBeatEvaluation()
        e.append(BeatEvaluation(DETECTIONS, ANNOTATIONS))
        # scores
        self.assertIsInstance(e.fmeasure, float)
        self.assertIsInstance(e.pscore, float)
        self.assertIsInstance(e.cemgil, float)
        self.assertIsInstance(e.goto, float)
        self.assertIsInstance(e.cmlc, float)
        self.assertIsInstance(e.cmlt, float)
        self.assertIsInstance(e.amlc, float)
        self.assertIsInstance(e.amlt, float)
        self.assertIsInstance(e.information_gain, float)
        self.assertIsInstance(e.global_information_gain, float)
        # error histogram
        self.assertIsInstance(e.error_histogram, np.ndarray)

    def test_results_empty(self):
        e = MeanBeatEvaluation()
        e.append(BeatEvaluation([], []))
        self.assertEqual(e.fmeasure, 1)
        self.assertEqual(e.pscore, 1)
        self.assertEqual(e.cemgil, 1)
        self.assertEqual(e.goto, 1)
        self.assertEqual(e.cmlc, 1)
        self.assertEqual(e.cmlt, 1)
        self.assertEqual(e.amlc, 1)
        self.assertEqual(e.amlt, 1)
        self.assertEqual(e.information_gain, np.log2(40))
        self.assertTrue(np.allclose(e.global_information_gain, np.log2(40)))
        self.assertTrue(np.allclose(e.error_histogram, np.zeros(40)))

    def test_results(self):
        e = MeanBeatEvaluation()
        e.append(BeatEvaluation(DETECTIONS, ANNOTATIONS))
        f = 2 * (8. / 10.) * (8. / 10.) / ((8. / 10.) + (8. / 10.))
        self.assertEqual(e.fmeasure, f)
        self.assertEqual(e.pscore, 9. / 10.)
        self.assertEqual(e.cemgil, 0.74710035298713695)
        self.assertEqual(e.goto, 1)
        self.assertEqual(e.cmlc, 0.4)
        self.assertEqual(e.cmlt, 0.8)
        self.assertEqual(e.amlc, 0.4)
        self.assertEqual(e.amlt, 0.8)
        self.assertEqual(e.information_gain, 3.965148445440323)
        self.assertEqual(e.global_information_gain, 3.965148445440323)
        error_histogram_ = np.zeros(40)
        error_histogram_[0] = 1
        error_histogram_[16] = 1
        error_histogram_[20] = 7
        error_histogram_[22] = 1
        self.assertTrue(np.allclose(e.error_histogram, error_histogram_))
