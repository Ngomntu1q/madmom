import numpy as np

CHORD_DTYPE = [('root', np.int), ('bass', np.int), ('interval', np.int, (12,))]

NO_CHORD = (-1, -1, np.zeros(12, dtype=np.int))
UNKNOWN_CHORD = (-1, -1, np.ones(12, dtype=np.int) * -1)


def chords(labels):
    crds = np.recarray(len(labels), dtype=CHORD_DTYPE)
    cache = {}
    for i, lbl in enumerate(labels):
        cv = cache.get(lbl, None)
        if cv is None:
            cv = chord(lbl)
            cache[lbl] = cv
            crds[i] = cv
        else:
            crds[i] = cv

    return crds


def chord(label):
    if label == 'N':
        return NO_CHORD
    if label == 'X':
        return UNKNOWN_CHORD

    c_idx = label.find(':')
    s_idx = label.find('/')

    if c_idx == -1:
        int_str = 'maj'
        if s_idx == -1:
            rt_str = label
            bs_str = ''
        else:
            rt_str = label[:s_idx]
            bs_str = label[s_idx + 1:]
    else:
        rt_str = label[:c_idx]
        if s_idx == -1:
            int_str = label[c_idx + 1:]
            bs_str = ''
        else:
            int_str = label[c_idx + 1:s_idx]
            bs_str = label[s_idx + 1:]

    root = pitch(rt_str)
    bass = interval(bs_str) if bs_str else 0
    ints = intervals(int_str)
    ints[bass] = 1

    return root, bass, ints


_l = [0, 1, 1, 0, 1, 1, 1]
_chroma_id = (np.arange(len(_l) * 2) + 1) + np.array(_l + _l).cumsum() - 1


def modify(base, modstr):
    for m in modstr:
        if m == 'b':
            base -= 1
        elif m == '#':
            base += 1
        else:
            raise ValueError('Unknown modifier: {}'.format(m))
    return base


def pitch(s):
    return modify(_chroma_id[(ord(s[0]) - ord('C')) % 7], s[1:]) % 12


def interval(s):
    for i, c in enumerate(s):
        if c.isdigit():
            return modify(_chroma_id[int(s[i:]) - 1], s[:i]) % 12


def interval_list(s, intervals=None):
    intervals = intervals if intervals is not None else np.zeros(12, dtype=np.int)
    for int_def in s[1:-1].split(','):
        int_def = int_def.strip()
        if int_def[0] == '*':
            intervals[interval(int_def[1:])] = 0
        else:
            intervals[interval(int_def)] = 1
    return intervals


_shorthands = {
    'maj': interval_list('(1,3,5)'),
    'min': interval_list('(1,b3,5)'),
    'dim': interval_list('(1,b3,b5)'),
    'aug': interval_list('(1,3,#5)'),
    'maj7': interval_list('(1,3,5,7)'),
    'min7': interval_list('(1,b3,5,b7)'),
    '7': interval_list('(1,3,5,b7)'),
    'dim7': interval_list('(1,b3,b5,bb7)'),
    'minmaj7': interval_list('(1,b3,5,7)'),
    'maj6': interval_list('(1,3,5,6)'),
    'min6': interval_list('(1,b3,5,b6)'),
    '9': interval_list('(1,3,5,b7,9)'),
    'maj9': interval_list('(1,3,5,7,9)'),
    'min9': interval_list('(1,b3,5,b7,9)'),
    'sus2': interval_list('(1,2,5)'),
    'sus4': interval_list('(1,4,5)'),
}


def intervals(s):
    list_idx = s.find('(')
    if list_idx == -1:
        return _shorthands[s].copy()
    if list_idx != 0:
        ivs = _shorthands[s[:list_idx]].copy()
    else:
        ivs = np.zeros(12, dtype=np.int)

    return interval_list(s[list_idx:], ivs)


def load_chords(filename):
    start, end, chord_labels = np.loadtxt(
            filename,
            dtype=[('start', np.float),
                   ('end', np.float),
                   ('chord', object)],
            unpack=True
    )

    crds = np.recarray(len(start),
                       dtype=[('start', np.float),
                              ('end', np.float),
                              ('chord', CHORD_DTYPE)]
                       )
    crds.start = start
    crds.end = end
    crds.chord = chords(chord_labels)
    return crds


def evaluation_pairs(ref_chords, est_chords):
    times = np.unique(np.hstack([ref_chords.start, ref_chords.end,
                                 est_chords.start, est_chords.end]))

    pairs = np.recarray(len(times) - 1,
                        dtype=[('duration', np.float),
                               ('ref_chord', CHORD_DTYPE),
                               ('est_chord', CHORD_DTYPE)])

    pairs.duration = times[1:] - times[:-1]
    pairs.ref_chord = ref_chords.chord[
        np.searchsorted(ref_chords.start, times[:-1], side='right') - 1]
    pairs.est_chord = est_chords.chord[
        np.searchsorted(est_chords.start, times[:-1], side='right') - 1]

    return pairs


def score_root(pairs):
    return (pairs.ref_chord.root == pairs.est_chord.root).astype(np.float)


def score_exact(pairs):
    return ((pairs.ref_chord.root == pairs.est_chord.root) &
            ((pairs.ref_chord.intervals ==
              pairs.est_chord.intervals).all(axis=1)))


def map_majmin(pairs):
    return


class ChordEvaluation(object):

    METRIC_NAMES = [
        ('root', 'Root'),
        ('majmin', 'MajMin')
    ]

    def __init__(self, detections, annotations):
        self.eval_pairs = evaluation_pairs(
            load_chords(detections),
            load_chords(annotations)
        )

    @property
    def root(self):
        return np.average(score_root(self.eval_pairs),
                          weights=self.eval_pairs.duration)

    @property
    def majmin(self):
        pass

