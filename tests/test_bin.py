# encoding: utf-8
# pylint: skip-file
"""
This file contains tests for the programs in the /bin directory.

"""

from __future__ import absolute_import, division, print_function

import unittest
import os
import subprocess
import tempfile

import numpy as np

from madmom.features import Activations

from . import AUDIO_PATH, ACTIVATIONS_PATH, DETECTIONS_PATH

tmp_file = tempfile.NamedTemporaryFile().name
sample_file = '%s/sample.wav' % AUDIO_PATH
stereo_sample_file = '%s/stereo_sample.wav' % AUDIO_PATH
program_path = os.path.dirname(os.path.realpath(__file__)) + '/../bin/'


def run_program(program):
    proc = subprocess.Popen(program, stdout=subprocess.PIPE, bufsize=-1)
    data, _ = proc.communicate()
    return bytes(data), proc.returncode


# TODO: parametrize tests, don't know how to do with nose, should be simple
#       with pytest: http://pytest.org/latest/parametrize.html

# TODO: can we speed up these tests?

class TestBeatDetectorProgram(unittest.TestCase):

    def setUp(self):
        self.bin = "%s/BeatDetector" % program_path
        self.activations = Activations("%s/sample.beats_blstm_2013.npz" %
                                       ACTIVATIONS_PATH)
        self.result = np.loadtxt("%s/sample.beat_detector.txt" %
                                 DETECTIONS_PATH)

    def test_help(self):
        _, ret_code = run_program([self.bin, '-h'])
        self.assertEqual(ret_code, 0)

    def test_binary(self):
        # save activations as binary file
        data, _ = run_program([self.bin, '--save', 'single', sample_file,
                               '-o', tmp_file])
        act = Activations(tmp_file)
        self.assertTrue(np.allclose(act, self.activations))
        self.assertEqual(act.fps, self.activations.fps)
        # reload from file
        data, _ = run_program([self.bin, '--load', 'single', tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_txt(self):
        # save activations as txt file
        data, _ = run_program([self.bin, '--save', '--sep', ' ', 'single',
                               sample_file, '-o', tmp_file])
        act = Activations(tmp_file, sep=' ', fps=100)
        self.assertTrue(np.allclose(act, self.activations, atol=1e-5))
        # reload from file
        data, _ = run_program([self.bin, '--load', '--sep', ' ', 'single',
                               tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_run(self):
        data, _ = run_program([self.bin, 'single', sample_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))


class TestBeatTrackerProgram(unittest.TestCase):

    def setUp(self):
        self.bin = "%s/BeatTracker" % program_path
        self.activations = Activations("%s/sample.beats_blstm_2013.npz" %
                                       ACTIVATIONS_PATH)
        self.result = np.loadtxt("%s/sample.beat_tracker.txt" %
                                 DETECTIONS_PATH)

    def test_help(self):
        _, ret_code = run_program([self.bin, '-h'])
        self.assertEqual(ret_code, 0)

    def test_binary(self):
        # save activations as binary file
        data, _ = run_program([self.bin, '--save', 'single', sample_file,
                               '-o', tmp_file])
        act = Activations(tmp_file)
        self.assertTrue(np.allclose(act, self.activations))
        self.assertEqual(act.fps, self.activations.fps)
        # reload from file
        data, _ = run_program([self.bin, '--load', 'single', tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_txt(self):
        # save activations as txt file
        data, _ = run_program([self.bin, '--save', '--sep', ' ', 'single',
                               sample_file, '-o', tmp_file])
        act = Activations(tmp_file, sep=' ', fps=100)
        self.assertTrue(np.allclose(act, self.activations, atol=1e-5))
        # reload from file
        data, _ = run_program([self.bin, '--load', '--sep', ' ', 'single',
                               tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_run(self):
        data, _ = run_program([self.bin, 'single', sample_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))


class TestComplexFluxProgram(unittest.TestCase):

    def setUp(self):
        self.bin = "%s/ComplexFlux" % program_path
        self.activations = Activations("%s/sample.complex_flux.npz" %
                                       ACTIVATIONS_PATH)
        self.result = np.loadtxt("%s/sample.complex_flux.txt" %
                                 DETECTIONS_PATH)

    def test_help(self):
        _, ret_code = run_program([self.bin, '-h'])
        self.assertEqual(ret_code, 0)

    def test_binary(self):
        # save activations as binary file
        data, _ = run_program([self.bin, '--save', 'single', sample_file,
                               '-o', tmp_file])
        act = Activations(tmp_file)
        self.assertTrue(np.allclose(act, self.activations))
        self.assertEqual(act.fps, self.activations.fps)
        # reload from file
        data, _ = run_program([self.bin, '--load', 'single', tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_txt(self):
        # save activations as txt file
        data, _ = run_program([self.bin, '--save', '--sep', ' ', 'single',
                               sample_file, '-o', tmp_file])
        act = Activations(tmp_file, sep=' ', fps=100)
        self.assertTrue(np.allclose(act, self.activations, atol=1e-5))
        # reload from file
        data, _ = run_program([self.bin, '--load', '--sep', ' ', 'single',
                               tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_run(self):
        data, _ = run_program([self.bin, 'single', sample_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))


class TestCRFBeatDetectorProgram(unittest.TestCase):

    def setUp(self):
        self.bin = "%s/CRFBeatDetector" % program_path
        self.activations = Activations("%s/sample.beats_blstm_2013.npz" %
                                       ACTIVATIONS_PATH)
        self.result = np.loadtxt("%s/sample.crf_beat_detector.txt" %
                                 DETECTIONS_PATH)

    def test_help(self):
        _, ret_code = run_program([self.bin, '-h'])
        self.assertEqual(ret_code, 0)

    def test_binary(self):
        # save activations as binary file
        data, _ = run_program([self.bin, '--save', 'single', sample_file,
                               '-o', tmp_file])
        act = Activations(tmp_file)
        self.assertTrue(np.allclose(act, self.activations))
        self.assertEqual(act.fps, self.activations.fps)
        # reload from file
        data, _ = run_program([self.bin, '--load', 'single', tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_txt(self):
        # save activations as txt file
        data, _ = run_program([self.bin, '--save', '--sep', ' ', 'single',
                               sample_file, '-o', tmp_file])
        act = Activations(tmp_file, sep=' ', fps=100)
        self.assertTrue(np.allclose(act, self.activations, atol=1e-5))
        # reload from file
        data, _ = run_program([self.bin, '--load', '--sep', ' ', 'single',
                               tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_run(self):
        data, _ = run_program([self.bin, 'single', sample_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))


class TestDBNBeatTrackerProgram(unittest.TestCase):

    def setUp(self):
        self.bin = "%s/DBNBeatTracker" % program_path
        self.activations = Activations("%s/sample.beats_blstm_2013.npz" %
                                       ACTIVATIONS_PATH)
        self.result = np.loadtxt("%s/sample.dbn_beat_tracker.txt" %
                                 DETECTIONS_PATH)

    def test_help(self):
        _, ret_code = run_program([self.bin, '-h'])
        self.assertEqual(ret_code, 0)

    def test_binary(self):
        # save activations as binary file
        data, _ = run_program([self.bin, '--save', 'single', sample_file,
                               '-o', tmp_file])
        act = Activations(tmp_file)
        self.assertTrue(np.allclose(act, self.activations))
        self.assertEqual(act.fps, self.activations.fps)
        # reload from file
        data, _ = run_program([self.bin, '--load', 'single', tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_txt(self):
        # save activations as txt file
        data, _ = run_program([self.bin, '--save', '--sep', ' ', 'single',
                               sample_file, '-o', tmp_file])
        act = Activations(tmp_file, sep=' ', fps=100)
        self.assertTrue(np.allclose(act, self.activations, atol=1e-5))
        # reload from file
        data, _ = run_program([self.bin, '--load', '--sep', ' ', 'single',
                               tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_run(self):
        data, _ = run_program([self.bin, 'single', sample_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))


class TestGMMPatternTrackerProgram(unittest.TestCase):

    def setUp(self):
        self.bin = "%s/GMMPatternTracker" % program_path
        self.activations = Activations("%s/sample.gmm_pattern_tracker.npz" %
                                       ACTIVATIONS_PATH)
        self.result = np.loadtxt("%s/sample.gmm_pattern_tracker.txt" %
                                 DETECTIONS_PATH)
        self.downbeat_result = self.result[self.result[:, 1] == 1][:, 0]

    def test_help(self):
        _, ret_code = run_program([self.bin, '-h'])
        self.assertEqual(ret_code, 0)

    def test_binary(self):
        # save activations as binary file
        data, _ = run_program([self.bin, '--save', 'single', sample_file,
                               '-o', tmp_file])
        act = Activations(tmp_file)
        self.assertTrue(np.allclose(act, self.activations))
        self.assertEqual(act.fps, self.activations.fps)
        # reload from file
        data, _ = run_program([self.bin, '--load', 'single', tmp_file])
        # need to reshape, since results are 2D
        result = np.fromstring(data, sep='\n').reshape((-1, 2))
        self.assertTrue(np.allclose(result, self.result))

    def test_txt(self):
        # save activations as txt file
        data, _ = run_program([self.bin, '--save', '--sep', ' ', 'single',
                               sample_file, '-o', tmp_file])
        act = Activations(tmp_file, sep=' ', fps=50)
        self.assertTrue(np.allclose(act, self.activations, atol=1e-5))
        # reload from file
        data, _ = run_program([self.bin, '--load', '--sep', ' ', 'single',
                               tmp_file])
        # need to reshape, since results are 2D
        result = np.fromstring(data, sep='\n').reshape((-1, 2))
        self.assertTrue(np.allclose(result, self.result))

    def test_run(self):
        data, _ = run_program([self.bin, 'single', sample_file])
        # need to reshape, since results are 2D
        result = np.fromstring(data, sep='\n').reshape((-1, 2))
        self.assertTrue(np.allclose(result, self.result))

    def test_run_downbeats(self):
        data, _ = run_program([self.bin, '--downbeats', 'single', sample_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.downbeat_result))


class TestLogFiltSpecFluxProgram(unittest.TestCase):

    def setUp(self):
        self.bin = "%s/LogFiltSpecFlux" % program_path
        self.activations = Activations("%s/sample.log_filt_spec_flux.npz" %
                                       ACTIVATIONS_PATH)
        self.result = np.loadtxt("%s/sample.log_filt_spec_flux.txt" %
                                 DETECTIONS_PATH)

    def test_help(self):
        _, ret_code = run_program([self.bin, '-h'])
        self.assertEqual(ret_code, 0)

    def test_binary(self):
        # save activations as binary file
        data, _ = run_program([self.bin, '--save', 'single', sample_file,
                               '-o', tmp_file])
        act = Activations(tmp_file)
        self.assertTrue(np.allclose(act, self.activations))
        self.assertEqual(act.fps, self.activations.fps)
        # reload from file
        data, _ = run_program([self.bin, '--load', 'single', tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_txt(self):
        # save activations as txt file
        data, _ = run_program([self.bin, '--save', '--sep', ' ', 'single',
                               sample_file, '-o', tmp_file])
        act = Activations(tmp_file, sep=' ', fps=100)
        self.assertTrue(np.allclose(act, self.activations, atol=1e-5))
        # reload from file
        data, _ = run_program([self.bin, '--load', '--sep', ' ', 'single',
                               tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_run(self):
        data, _ = run_program([self.bin, 'single', sample_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))


class TestMMBeatTrackerProgram(unittest.TestCase):
    def setUp(self):
        self.bin = "%s/MMBeatTracker" % program_path
        self.activations = Activations("%s/sample.beats_blstm_mm_2013.npz" %
                                       ACTIVATIONS_PATH)
        self.result = np.loadtxt("%s/sample.mm_beat_tracker.txt" %
                                 DETECTIONS_PATH)

    def test_help(self):
        _, ret_code = run_program([self.bin, '-h'])
        self.assertEqual(ret_code, 0)

    def test_binary(self):
        # save activations as binary file
        data, _ = run_program([self.bin, '--save', 'single', sample_file,
                               '-o', tmp_file])
        act = Activations(tmp_file)
        self.assertTrue(np.allclose(act, self.activations))
        self.assertEqual(act.fps, self.activations.fps)
        # reload from file
        data, _ = run_program([self.bin, '--load', 'single', tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_txt(self):
        # save activations as txt file
        data, _ = run_program([self.bin, '--save', '--sep', ' ', 'single',
                               sample_file, '-o', tmp_file])
        act = Activations(tmp_file, sep=' ', fps=100)
        self.assertTrue(np.allclose(act, self.activations, atol=1e-5))
        # reload from file
        data, _ = run_program([self.bin, '--load', '--sep', ' ', 'single',
                               tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_run(self):
        data, _ = run_program([self.bin, 'single', sample_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))


class TestOnsetDetectorProgram(unittest.TestCase):
    def setUp(self):
        self.bin = "%s/OnsetDetector" % program_path
        self.activations = Activations("%s/sample.onsets_brnn_2013.npz" %
                                       ACTIVATIONS_PATH)
        self.result = np.loadtxt("%s/sample.onset_detector.txt" %
                                 DETECTIONS_PATH)

    def test_help(self):
        _, ret_code = run_program([self.bin, '-h'])
        self.assertEqual(ret_code, 0)

    def test_binary(self):
        # save activations as binary file
        data, _ = run_program([self.bin, '--save', 'single', sample_file,
                               '-o', tmp_file])
        act = Activations(tmp_file)
        self.assertTrue(np.allclose(act, self.activations))
        self.assertEqual(act.fps, self.activations.fps)
        # reload from file
        data, _ = run_program([self.bin, '--load', 'single', tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_txt(self):
        # save activations as txt file
        data, _ = run_program([self.bin, '--save', '--sep', ' ', 'single',
                               sample_file, '-o', tmp_file])
        act = Activations(tmp_file, sep=' ', fps=100)
        self.assertTrue(np.allclose(act, self.activations, atol=1e-5))
        # reload from file
        data, _ = run_program([self.bin, '--load', '--sep', ' ', 'single',
                               tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_run(self):
        data, _ = run_program([self.bin, 'single', sample_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))


class TestOnsetDetectorLLProgram(unittest.TestCase):
    def setUp(self):
        self.bin = "%s/OnsetDetectorLL" % program_path
        self.activations = Activations("%s/sample.onsets_rnn_2013.npz" %
                                       ACTIVATIONS_PATH)
        self.result = np.loadtxt("%s/sample.onset_detector_ll.txt" %
                                 DETECTIONS_PATH)

    def test_help(self):
        _, ret_code = run_program([self.bin, '-h'])
        self.assertEqual(ret_code, 0)

    def test_binary(self):
        # save activations as binary file
        data, _ = run_program([self.bin, '--save', 'single', sample_file,
                               '-o', tmp_file])
        act = Activations(tmp_file)
        self.assertTrue(np.allclose(act, self.activations))
        self.assertEqual(act.fps, self.activations.fps)
        # reload from file
        data, _ = run_program([self.bin, '--load', 'single', tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_txt(self):
        # save activations as txt file
        data, _ = run_program([self.bin, '--save', '--sep', ' ', 'single',
                               sample_file, '-o', tmp_file])
        act = Activations(tmp_file, sep=' ', fps=100)
        self.assertTrue(np.allclose(act, self.activations, atol=1e-5))
        # reload from file
        data, _ = run_program([self.bin, '--load', '--sep', ' ', 'single',
                               tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_run(self):
        data, _ = run_program([self.bin, 'single', sample_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))


class TestPianoTranscriptorProgram(unittest.TestCase):
    def setUp(self):
        self.bin = "%s/PianoTranscriptor" % program_path
        self.activations = Activations("%s/stereo_sample.notes_brnn_2013.npz" %
                                       ACTIVATIONS_PATH)
        self.result = np.loadtxt("%s/stereo_sample.pianot_ranscriptor.txt" %
                                 DETECTIONS_PATH)

    def test_help(self):
        _, ret_code = run_program([self.bin, '-h'])
        self.assertEqual(ret_code, 0)

    def test_binary(self):
        # save activations as binary file
        data, _ = run_program([self.bin, '--save', 'single',
                               stereo_sample_file, '-o', tmp_file])
        act = Activations(tmp_file)
        self.assertTrue(np.allclose(act, self.activations, atol=1e-5))
        self.assertEqual(act.fps, self.activations.fps)
        # reload from file
        data, _ = run_program([self.bin, '--load', 'single', tmp_file])
        # need to reshape, since results are 2D
        result = np.fromstring(data, sep='\n').reshape((-1, 2))
        self.assertTrue(np.allclose(result, self.result))

    def test_txt(self):
        # save activations as txt file
        data, _ = run_program([self.bin, '--save', '--sep', ' ', 'single',
                               stereo_sample_file, '-o', tmp_file])
        act = Activations(tmp_file, sep=' ', fps=100)
        self.assertTrue(np.allclose(act, self.activations, atol=1e-5))
        # reload from file
        data, _ = run_program([self.bin, '--load', '--sep', ' ', 'single',
                               tmp_file])
        # need to reshape, since results are 2D
        result = np.fromstring(data, sep='\n').reshape((-1, 2))
        self.assertTrue(np.allclose(result, self.result))

    def test_run(self):
        data, _ = run_program([self.bin, 'single', stereo_sample_file])
        # need to reshape, since results are 2D
        result = np.fromstring(data, sep='\n').reshape((-1, 2))
        self.assertTrue(np.allclose(result, self.result))


class TestSpectralOnsetDetectionProgram(unittest.TestCase):

    def setUp(self):
        self.bin = "%s/SpectralOnsetDetection" % program_path
        self.activations = Activations("%s/sample.spectral_flux.npz" %
                                       ACTIVATIONS_PATH)
        self.result = np.loadtxt("%s/sample.spectral_flux.txt" %
                                 DETECTIONS_PATH)

    def test_help(self):
        _, ret_code = run_program([self.bin, '-h'])
        self.assertEqual(ret_code, 0)

    def test_binary(self):
        # save activations as binary file
        data, _ = run_program([self.bin, '--save', 'single', sample_file,
                               '-o', tmp_file])
        act = Activations(tmp_file)
        self.assertTrue(np.allclose(act, self.activations))
        self.assertEqual(act.fps, self.activations.fps)
        # reload from file
        data, _ = run_program([self.bin, '--load', 'single', tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_txt(self):
        # save activations as txt file
        data, _ = run_program([self.bin, '--save', '--sep', ' ', 'single',
                               sample_file, '-o', tmp_file])
        act = Activations(tmp_file, sep=' ', fps=100)
        self.assertTrue(np.allclose(act, self.activations, atol=1e-5))
        # reload from file
        data, _ = run_program([self.bin, '--load', '--sep', ' ', 'single',
                               tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_run(self):
        data, _ = run_program([self.bin, 'single', sample_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))


class TestSuperFluxProgram(unittest.TestCase):

    def setUp(self):
        self.bin = "%s/SuperFlux" % program_path
        self.activations = Activations("%s/sample.super_flux.npz" %
                                       ACTIVATIONS_PATH)
        self.result = np.loadtxt("%s/sample.super_flux.txt" % DETECTIONS_PATH)

    def test_help(self):
        _, ret_code = run_program([self.bin, '-h'])
        self.assertEqual(ret_code, 0)

    def test_binary(self):
        # save activations as binary file
        data, _ = run_program([self.bin, '--save', 'single', sample_file,
                               '-o', tmp_file])
        act = Activations(tmp_file)
        self.assertTrue(np.allclose(act, self.activations))
        self.assertEqual(act.fps, self.activations.fps)
        # reload from file
        data, _ = run_program([self.bin, '--load', 'single', tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_txt(self):
        # save activations as txt file
        data, _ = run_program([self.bin, '--save', '--sep', ' ', 'single',
                               sample_file, '-o', tmp_file])
        act = Activations(tmp_file, sep=' ', fps=200)
        self.assertTrue(np.allclose(act, self.activations, atol=1e-5))
        # reload from file
        data, _ = run_program([self.bin, '--load', '--sep', ' ', 'single',
                               tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_run(self):
        data, _ = run_program([self.bin, 'single', sample_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))


class TestSuperFluxNNProgram(unittest.TestCase):

    def setUp(self):
        self.bin = "%s/SuperFluxNN" % program_path
        self.activations = Activations("%s/sample.super_flux_nn.npz" %
                                       ACTIVATIONS_PATH)
        self.result = np.loadtxt("%s/sample.super_flux_nn.txt" %
                                 DETECTIONS_PATH)

    def test_help(self):
        _, ret_code = run_program([self.bin, '-h'])
        self.assertEqual(ret_code, 0)

    def test_binary(self):
        # save activations as binary file
        data, _ = run_program([self.bin, '--save', 'single', sample_file,
                               '-o', tmp_file])
        act = Activations(tmp_file)
        self.assertTrue(np.allclose(act, self.activations))
        self.assertEqual(act.fps, self.activations.fps)
        # reload from file
        data, _ = run_program([self.bin, '--load', 'single', tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_txt(self):
        # save activations as txt file
        data, _ = run_program([self.bin, '--save', '--sep', ' ', 'single',
                               sample_file, '-o', tmp_file])
        act = Activations(tmp_file, sep=' ', fps=100)
        self.assertTrue(np.allclose(act, self.activations, atol=1e-5))
        # reload from file
        data, _ = run_program([self.bin, '--load', '--sep', ' ', 'single',
                               tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_run(self):
        data, _ = run_program([self.bin, 'single', sample_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))


class TestTempoDetectorProgram(unittest.TestCase):

    def setUp(self):
        self.bin = "%s/TempoDetector" % program_path
        self.activations = Activations("%s/sample.beats_blstm_2013.npz" %
                                       ACTIVATIONS_PATH)
        self.result = np.loadtxt("%s/sample.tempo_detector.txt" %
                                 DETECTIONS_PATH)

    def test_help(self):
        _, ret_code = run_program([self.bin, '-h'])
        self.assertEqual(ret_code, 0)

    def test_binary(self):
        # save activations as binary file
        data, _ = run_program([self.bin, '--save', 'single', sample_file,
                               '-o', tmp_file])
        act = Activations(tmp_file)
        self.assertTrue(np.allclose(act, self.activations))
        self.assertEqual(act.fps, self.activations.fps)
        # reload from file
        data, _ = run_program([self.bin, '--load', 'single', tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_txt(self):
        # save activations as txt file
        data, _ = run_program([self.bin, '--save', '--sep', ' ', 'single',
                               sample_file, '-o', tmp_file])
        act = Activations(tmp_file, sep=' ', fps=100)
        self.assertTrue(np.allclose(act, self.activations, atol=1e-5))
        # reload from file
        data, _ = run_program([self.bin, '--load', '--sep', ' ', 'single',
                               tmp_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))

    def test_run(self):
        data, _ = run_program([self.bin, 'single', sample_file])
        result = np.fromstring(data, sep='\n')
        self.assertTrue(np.allclose(result, self.result))
