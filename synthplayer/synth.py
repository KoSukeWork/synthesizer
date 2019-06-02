"""
Sample waveform synthesizer. Inspired by FM synthesizers such as the Yamaha DX-7 and TX81Z.
Creates various waveform samples with adjustable parameters.

Written by Irmen de Jong (irmen@razorvine.net) - License: GNU LGPL 3.
"""

import itertools
from typing import Optional, Generator, List, Tuple
from . import params
from .sample import Sample
from .oscillators import *


__all__ = ["key_num", "key_freq", "note_freq", "octave_notes", "note_alias",
           "major_chords", "major_chord_keys", "WaveSynth"]


octave_notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


note_alias = {
    'C': 'C',
    'C#': 'C#',
    'C##': 'D',
    'D': 'D',
    'D#': 'D#',
    'E': 'E',
    'E#': 'F',
    'F': 'F',
    'F#': 'F#',
    'F##': 'G',
    'G': 'G',
    'G#': 'G#',
    'G##': 'A',
    'A': 'A',
    'A#': 'A#',
    'B': 'B',
    'B#': 'C'
}


major_chords = {
    # from https://en.wikipedia.org/wiki/Major_seventh_chord
    # a one in the number tuple means that the note is from the next higher octave
    'C':  (('C', 'E', 'G', 'B'),       (0, 0, 0, 0)),
    'C#': (('C#', 'E#', 'G#', 'B#'),   (0, 0, 0, 1)),
    'D':  (('D', 'F#', 'A', 'C'),      (0, 0, 0, 1)),
    'D#': (('D#', 'F##', 'A#', 'C##'), (0, 0, 0, 1)),
    'E':  (('E', 'G#', 'B', 'D#'),     (0, 0, 0, 1)),
    'F':  (('F', 'A', 'C', 'E'),       (0, 0, 1, 1)),
    'F#': (('F#', 'A#', 'C#', 'E#'),   (0, 0, 1, 1)),
    'G':  (('G', 'B', 'D', 'F#'),      (0, 0, 1, 1)),
    'G#': (('G#', 'B#', 'D#', 'F##'),  (0, 1, 1, 1)),
    'A':  (('A', 'C#', 'E', 'G#'),     (0, 1, 1, 1)),
    'A#': (('A#', 'C##', 'E#', 'G##'), (0, 1, 1, 1)),
    'B':  (('B', 'D#', 'F#', 'A#'),    (0, 1, 1, 1)),
}


def major_chord_keys(rootnote: str, octave: int) -> Tuple[Tuple[str, int], Tuple[str, int], Tuple[str, int], Tuple[str, int]]:
    keys, octaves = major_chords[rootnote.upper()]
    return (note_alias[keys[0]], octave+octaves[0]),\
           (note_alias[keys[1]], octave+octaves[1]),\
           (note_alias[keys[2]], octave+octaves[2]),\
           (note_alias[keys[3]], octave+octaves[3])


def key_num(note: str, octave: int) -> int:
    notes = {
        "C":   4,
        "C#":  5,
        "D":   6,
        "D#":  7,
        "E":   8,
        "F":   9,
        "F#": 10,
        "G":  11,
        "G#": 12,
        "A":  13,
        "A#": 14,
        "B":  15
    }
    return (octave-1)*12 + notes[note.upper()]


def key_freq(key_number: int, a4: float = 440.0) -> float:
    """
    Return the note frequency for the given piano key number.
    C4 is key 40 and A4 is key 49 (=440 hz).
    https://en.wikipedia.org/wiki/Piano_key_frequencies
    """
    return 2**((key_number-49)/12) * a4


def note_freq(note: str, octave: Optional[int] = None, a4: float = 440.0) -> float:
    """
    Return the frequency for the given note in the octave.
    Note can be like 'c#4' (= c# in 4th octave) or just 'c#' + specify octave separately.
    """
    if not octave:
        octave = int(note[-1:])
        note = note[:-1]
    return key_freq(key_num(note, octave), a4)


class WaveSynth:
    """
    Waveform sample synthesizer. Can generate various wave forms based on mathematic functions:
    sine, square (perfect or with harmonics), triangle, sawtooth (perfect or with harmonics),
    variable harmonics, white noise.  It also supports an optional LFO for Frequency Modulation.
    The resulting waveform sample data is in integer 16 or 32 bits format.
    """
    def __init__(self, samplerate: int = 0, samplewidth: int = 0) -> None:
        samplewidth = samplewidth or params.norm_samplewidth
        if samplewidth not in (2, 4):
            raise ValueError("only sample widths 2 and 4 are supported")
        self.samplerate = samplerate or params.norm_samplerate
        self.samplewidth = samplewidth

    def sine(self, frequency: int, duration: float, amplitude: float = 0.9999, phase: float = 0.0,
             bias: float = 0.0, fm_lfo: Optional[Oscillator] = None) -> Sample:
        """Simple sine wave. Optional FM using a supplied LFO."""
        wave = self.__sine(frequency, amplitude, phase, bias, fm_lfo)
        return Sample.from_oscillator(wave, duration)

    def sine_gen(self, frequency: int, amplitude: float = 0.9999, phase: float = 0.0,
                 bias: float = 0.0, fm_lfo: Optional[Oscillator] = None) -> Generator[List[int], None, None]:
        """Simple sine wave generator. Optional FM using a supplied LFO."""
        wave = self.__sine(frequency, amplitude, phase, bias, fm_lfo).blocks()
        while True:
            block = next(wave)
            yield list(map(int, block))

    def square(self, frequency: int, duration: float, amplitude: float = 0.75, phase: float = 0.0,
               bias: float = 0.0, fm_lfo: Optional[Oscillator] = None) -> Sample:
        """
        A perfect square wave [max/-max].
        It is fast, but the square wave is not as 'natural' sounding as the ones
        generated by the square_h function (which is based on harmonics).
        """
        wave = self.__square(frequency, amplitude, phase, bias, fm_lfo)
        return Sample.from_oscillator(wave, duration)

    def square_gen(self, frequency: int, amplitude: float = 0.75, phase: float = 0.0,
                   bias: float = 0.0, fm_lfo: Optional[Oscillator] = None) -> Generator[List[int], None, None]:
        """
        Generator for a perfect square wave [max/-max].
        It is fast, but the square wave is not as 'natural' sounding as the ones
        generated by the square_h function (which is based on harmonics).
        """
        wave = self.__square(frequency, amplitude, phase, bias, fm_lfo).blocks()
        while True:
            block = next(wave)
            yield list(map(int, block))

    def square_h(self, frequency: int, duration: float, num_harmonics: int = 16, amplitude: float = 0.9999,
                 phase: float = 0.0, bias: float = 0.0, fm_lfo: Optional[Oscillator] = None) -> Sample:
        """A square wave based on harmonic sine waves (more natural sounding than pure square)"""
        wave = self.__square_h(frequency, num_harmonics, amplitude, phase, bias, fm_lfo)
        return Sample.from_oscillator(wave, duration)

    def square_h_gen(self, frequency: int, num_harmonics: int = 16, amplitude: float = 0.9999, phase: float = 0.0,
                     bias: float = 0.0, fm_lfo: Optional[Oscillator] = None) -> Generator[List[int], None, None]:
        """Generator for a square wave based on harmonic sine waves (more natural sounding than pure square)"""
        wave = self.__square_h(frequency, num_harmonics, amplitude, phase, bias, fm_lfo).blocks()
        while True:
            block = next(wave)
            yield list(map(int, block))

    def triangle(self, frequency: int, duration: float, amplitude: float = 0.9999, phase: float = 0.0,
                 bias: float = 0.0, fm_lfo: Optional[Oscillator] = None) -> Sample:
        """Perfect triangle waveform (not using harmonics). Optional FM using a supplied LFO."""
        wave = self.__triangle(frequency, amplitude, phase, bias, fm_lfo)
        return Sample.from_oscillator(wave, duration)

    def triangle_gen(self, frequency: int, amplitude: float = 0.9999, phase: float = 0.0,
                     bias: float = 0.0, fm_lfo: Optional[Oscillator] = None) -> Generator[List[int], None, None]:
        """Generator for a perfect triangle waveform (not using harmonics). Optional FM using a supplied LFO."""
        wave = self.__triangle(frequency, amplitude, phase, bias, fm_lfo).blocks()
        while True:
            block = next(wave)
            yield list(map(int, block))

    def sawtooth(self, frequency: int, duration: float, amplitude: float = 0.75, phase: float = 0.0,
                 bias: float = 0.0, fm_lfo: Optional[Oscillator] = None) -> Sample:
        """Perfect sawtooth waveform (not using harmonics)."""
        wave = self.__sawtooth(frequency, amplitude, phase, bias, fm_lfo)
        return Sample.from_oscillator(wave, duration)

    def sawtooth_gen(self, frequency: int, amplitude: float = 0.75, phase: float = 0.0,
                     bias: float = 0.0, fm_lfo: Optional[Oscillator] = None) -> Generator[List[int], None, None]:
        """Generator for a perfect sawtooth waveform (not using harmonics)."""
        wave = self.__sawtooth(frequency, amplitude, phase, bias, fm_lfo).blocks()
        while True:
            block = next(wave)
            yield list(map(int, block))

    def sawtooth_h(self, frequency: int, duration: float, num_harmonics: int = 16, amplitude: float = 0.5,
                   phase: float = 0.0, bias: float = 0.0, fm_lfo: Optional[Oscillator] = None) -> Sample:
        """Sawtooth waveform based on harmonic sine waves"""
        wave = self.__sawtooth_h(frequency, num_harmonics, amplitude, phase, bias, fm_lfo)
        return Sample.from_oscillator(wave, duration)

    def sawtooth_h_gen(self, frequency: int, num_harmonics: int = 16, amplitude: float = 0.5,
                       phase: float = 0.0, bias: float = 0.0, fm_lfo: Optional[Oscillator] = None) -> Generator[List[int], None, None]:
        """Generator for a Sawtooth waveform based on harmonic sine waves"""
        wave = self.__sawtooth_h(frequency, num_harmonics, amplitude, phase, bias, fm_lfo).blocks()
        while True:
            block = next(wave)
            yield list(map(int, block))

    def pulse(self, frequency: int, duration: float, amplitude: float = 0.75, phase: float = 0.0,
              bias: float = 0.0, pulsewidth: float = 0.1,
              fm_lfo: Optional[Oscillator] = None, pwm_lfo: Optional[Oscillator] = None) -> Sample:
        """
        Perfect pulse waveform (not using harmonics).
        Optional FM and/or Pulse-width modulation. If you use PWM, pulsewidth is ignored.
        The pwm_lfo oscillator should yield values between 0 and 1 (=the pulse width factor), or it will be clipped.
        """
        wave = self.__pulse(frequency, amplitude, phase, bias, pulsewidth, fm_lfo, pwm_lfo)
        return Sample.from_oscillator(wave, duration)

    def pulse_gen(self, frequency: int, amplitude: float = 0.75, phase: float = 0.0, bias: float = 0.0,
                  pulsewidth: float = 0.1, fm_lfo: Optional[Oscillator] = None,
                  pwm_lfo: Optional[Oscillator] = None) -> Generator[List[int], None, None]:
        """
        Generator for perfect pulse waveform (not using harmonics).
        Optional FM and/or Pulse-width modulation. If you use PWM, pulsewidth is ignored.
        The pwm_lfo oscillator should yield values between 0 and 1 (=the pulse width factor), or it will be clipped.
        """
        wave = self.__pulse(frequency, amplitude, phase, bias, pulsewidth, fm_lfo, pwm_lfo).blocks()
        while True:
            block = next(wave)
            yield list(map(int, block))

    def harmonics(self, frequency: int, duration: float, harmonics: List[Tuple[int, float]],
                  amplitude: float = 0.5, phase: float = 0.0, bias: float = 0.0, fm_lfo: Optional[Oscillator] = None) -> Sample:
        """Makes a waveform based on harmonics. This is slow because many sine waves are added together."""
        wave = self.__harmonics(frequency, harmonics, amplitude, phase, bias, fm_lfo)
        return Sample.from_oscillator(wave, duration)

    def harmonics_gen(self, frequency: int, harmonics: List[Tuple[int, float]],
                      amplitude: float = 0.5, phase: float = 0.0, bias: float = 0.0,
                      fm_lfo: Optional[Oscillator] = None) -> Generator[List[int], None, None]:
        """Generator for a waveform based on harmonics. This is slow because many sine waves are added together."""
        wave = self.__harmonics(frequency, harmonics, amplitude, phase, bias, fm_lfo).blocks()
        while True:
            block = next(wave)
            yield list(map(int, block))

    def white_noise(self, frequency: int, duration: float, amplitude: float = 0.9999, bias: float = 0.0) -> Sample:
        """White noise (randomness) waveform."""
        wave = self.__white_noise(frequency, amplitude, bias)
        return Sample.from_oscillator(wave, duration)

    def white_noise_gen(self, frequency: int, amplitude: float = 0.9999, bias: float = 0.0) -> Generator[List[int], None, None]:
        """Generator for White noise (randomness) waveform."""
        wave = self.__white_noise(frequency, amplitude, bias).blocks()
        while True:
            block = next(wave)
            yield list(map(int, block))

    def semicircle(self, frequency: int, duration: float, amplitude: float = 0.9999, phase: float = 0.0,
                   bias: float = 0.0, fm_lfo: Optional[Oscillator] = None) -> Sample:
        """Semicircle half ('W3'). Optional FM using a supplied LFO."""
        wave = self.__semicircle(frequency, amplitude, phase, bias, fm_lfo)
        return Sample.from_oscillator(wave, duration)

    def semicircle_gen(self, frequency: int, amplitude: float = 0.9999, phase: float = 0.0,
                       bias: float = 0.0, fm_lfo: Optional[Oscillator] = None) -> Generator[List[int], None, None]:
        """Semicircle half ('W3') generator. Optional FM using a supplied LFO."""
        wave = self.__semicircle(frequency, amplitude, phase, bias, fm_lfo).blocks()
        while True:
            block = next(wave)
            yield list(map(int, block))

    def pointy(self, frequency: int, duration: float, amplitude: float = 0.9999,
               phase: float = 0.0, bias: float = 0.0, fm_lfo: Optional[Oscillator] = None) -> Sample:
        """Pointy 'inverted cosine' ('W2'). Optional FM using a supplied LFO."""
        wave = self.__pointy(frequency, amplitude, phase, bias, fm_lfo)
        return Sample.from_oscillator(wave, duration)

    def pointy_gen(self, frequency: int, amplitude: float = 0.9999, phase: float = 0.0, bias: float = 0.0,
                   fm_lfo: Optional[Oscillator] = None) -> Generator[List[int], None, None]:
        """Pointy 'inverted cosine' ('W2') generator. Optional FM using a supplied LFO."""
        wave = self.__pointy(frequency, amplitude, phase, bias, fm_lfo).blocks()
        while True:
            block = next(wave)
            yield list(map(int, block))

    # note: 'linear'  is not offered as a sampled waveform directly, because this LFO it makes little sense as a sample

    def __sine(self, frequency: int, amplitude: float, phase: float, bias: float, fm_lfo: Optional[Oscillator]) -> Oscillator:
        scale = self.__check_and_get_scale(frequency, amplitude, bias)
        if fm_lfo:
            return Sine(frequency, amplitude*scale, phase, bias*scale, fm_lfo=fm_lfo, samplerate=self.samplerate)
        else:
            return FastSine(frequency, amplitude*scale, phase, bias*scale, samplerate=self.samplerate)

    def __semicircle(self, frequency: int, amplitude: float, phase: float, bias: float, fm_lfo: Optional[Oscillator]) -> Oscillator:
        scale = self.__check_and_get_scale(frequency, amplitude, bias)
        if fm_lfo:
            return Semicircle(frequency, amplitude*scale, phase, bias*scale, fm_lfo=fm_lfo, samplerate=self.samplerate)
        else:
            return FastSemicircle(frequency, amplitude*scale, phase, bias*scale, samplerate=self.samplerate)

    def __pointy(self, frequency: int, amplitude: float, phase: float, bias: float, fm_lfo: Optional[Oscillator]) -> Oscillator:
        scale = self.__check_and_get_scale(frequency, amplitude, bias)
        if fm_lfo:
            return Pointy(frequency, amplitude*scale, phase, bias*scale, fm_lfo=fm_lfo, samplerate=self.samplerate)
        else:
            return FastPointy(frequency, amplitude*scale, phase, bias*scale, samplerate=self.samplerate)

    def __square(self, frequency: int, amplitude: float, phase: float, bias: float, fm_lfo: Optional[Oscillator]) -> Oscillator:
        scale = self.__check_and_get_scale(frequency, amplitude, bias)
        if fm_lfo:
            return Square(frequency, amplitude*scale, phase, bias*scale, fm_lfo=fm_lfo, samplerate=self.samplerate)
        else:
            return FastSquare(frequency, amplitude*scale, phase, bias*scale, samplerate=self.samplerate)

    def __square_h(self, frequency: int, num_harmonics: int, amplitude: float,
                   phase: float, bias: float, fm_lfo: Optional[Oscillator]) -> Oscillator:
        scale = self.__check_and_get_scale(frequency, amplitude, bias)
        return SquareH(frequency, num_harmonics, amplitude*scale, phase, bias*scale, fm_lfo=fm_lfo, samplerate=self.samplerate)

    def __triangle(self, frequency: int, amplitude: float, phase: float, bias: float, fm_lfo: Optional[Oscillator]) -> Oscillator:
        scale = self.__check_and_get_scale(frequency, amplitude, bias)
        if fm_lfo:
            return Triangle(frequency, amplitude*scale, phase, bias*scale, fm_lfo=fm_lfo, samplerate=self.samplerate)
        else:
            return FastTriangle(frequency, amplitude*scale, phase, bias*scale, samplerate=self.samplerate)

    def __sawtooth(self, frequency: int, amplitude: float, phase: float, bias: float, fm_lfo: Optional[Oscillator]) -> Oscillator:
        scale = self.__check_and_get_scale(frequency, amplitude, bias)
        if fm_lfo:
            return Sawtooth(frequency, amplitude*scale, phase, bias*scale, fm_lfo=fm_lfo, samplerate=self.samplerate)
        else:
            return FastSawtooth(frequency, amplitude*scale, phase, bias*scale, samplerate=self.samplerate)

    def __sawtooth_h(self, frequency: int, num_harmonics: int, amplitude: float,
                     phase: float, bias: float, fm_lfo: Optional[Oscillator]) -> Oscillator:
        scale = self.__check_and_get_scale(frequency, amplitude, bias)
        return SawtoothH(frequency, num_harmonics, amplitude*scale, phase, bias*scale, fm_lfo=fm_lfo, samplerate=self.samplerate)

    def __pulse(self, frequency: int, amplitude: float, phase: float, bias: float,
                pulsewidth: float, fm_lfo: Optional[Oscillator], pwm_lfo: Optional[Oscillator]) -> Oscillator:
        assert 0 <= pulsewidth <= 1
        scale = self.__check_and_get_scale(frequency, amplitude, bias)
        if fm_lfo:
            return Pulse(frequency, amplitude*scale, phase, bias*scale, pulsewidth,
                         fm_lfo=fm_lfo, pwm_lfo=pwm_lfo, samplerate=self.samplerate)
        else:
            return FastPulse(frequency, amplitude*scale, phase, bias*scale, pulsewidth,
                             pwm_lfo=pwm_lfo, samplerate=self.samplerate)

    def __harmonics(self, frequency: int, harmonics: List[Tuple[int, float]], amplitude: float,
                    phase: float, bias: float, fm_lfo: Optional[Oscillator]) -> Oscillator:
        scale = self.__check_and_get_scale(frequency, amplitude, bias)
        return Harmonics(frequency, harmonics, amplitude*scale, phase, bias*scale, fm_lfo=fm_lfo, samplerate=self.samplerate)

    def __white_noise(self, frequency: int, amplitude: float, bias: float) -> Oscillator:
        scale = self.__check_and_get_scale(frequency, amplitude, bias)
        return WhiteNoise(frequency, amplitude*scale, bias*scale, samplerate=self.samplerate)

    def __check_and_get_scale(self, freq: float, amplitude: float, bias: float) -> int:
        assert freq <= self.samplerate/2    # don't exceed the Nyquist frequency
        assert 0 <= amplitude <= 1.0
        assert -1 <= bias <= 1.0
        scale = 2 ** (self.samplewidth * 8 - 1) - 1      # type: int
        return scale


def check_waveforms() -> None:
    # white noise frequency issue test
    wn = WhiteNoise(100, samplerate=1000)
    list(itertools.islice(wn.blocks(), 10))
    wn = WhiteNoise(1000, samplerate=1000)
    list(itertools.islice(wn.blocks(), 10))
    wn = WhiteNoise(1001, samplerate=1000)
    try:
        list(itertools.islice(wn.blocks(), 10))
        raise SystemExit("invalid white noise freq should raise exception")
    except ValueError:
        pass

    # check the wavesynth and generators
    ws = WaveSynth(samplerate=1000)
    s = ws.sine(440, 1.024)
    sgen = ws.sine_gen(440)
    s2 = sum(itertools.islice(sgen, 0, 2), [])
    assert list(s.get_frame_array()) == s2
    s = ws.square(440, 1.024)
    sgen = ws.square_gen(440)
    s2 = sum(itertools.islice(sgen, 0, 2), [])
    assert list(s.get_frame_array()) == s2
    s = ws.square_h(440, 1.024)
    sgen = ws.square_h_gen(440)
    s2 = sum(itertools.islice(sgen, 0, 2), [])
    assert list(s.get_frame_array()) == s2
    s = ws.triangle(440, 1.024)
    sgen = ws.triangle_gen(440)
    s2 = sum(itertools.islice(sgen, 0, 2), [])
    assert list(s.get_frame_array()) == s2
    s = ws.sawtooth(440, 1.024)
    sgen = ws.sawtooth_gen(440)
    s2 = sum(itertools.islice(sgen, 0, 2), [])
    assert list(s.get_frame_array()) == s2
    s = ws.sawtooth_h(440, 1.024)
    sgen = ws.sawtooth_h_gen(440)
    s2 = sum(itertools.islice(sgen, 0, 2), [])
    assert list(s.get_frame_array()) == s2
    s = ws.pulse(440, 1.024)
    sgen = ws.pulse_gen(440)
    s2 = sum(itertools.islice(sgen, 0, 2), [])
    assert list(s.get_frame_array()) == s2
    s = ws.harmonics(440, 1.024, [(n, 1/n) for n in range(1, 8)])
    sgen = ws.harmonics_gen(440, [(n, 1/n) for n in range(1, 8)])
    s2 = sum(itertools.islice(sgen, 0, 2), [])
    assert list(s.get_frame_array()) == s2
    s = ws.white_noise(440, 1)
    sgen = ws.white_noise_gen(440)
    s2 = sum(itertools.islice(sgen, 0, 2), [])
    assert len(s) == 1000
    assert len(s2) == 2*params.norm_osc_blocksize
    s = ws.semicircle(440, 1)
    sgen = ws.semicircle_gen(440)
    s2 = sum(itertools.islice(sgen, 0, 2), [])
    assert len(s) == 1000
    assert len(s2) == 2*params.norm_osc_blocksize


def plot_waveforms() -> None:
    import matplotlib.pyplot as plot

    def get_data(osc: Oscillator) -> List[float]:
        return next(osc.blocks())

    ws = WaveSynth(samplerate=params.norm_osc_blocksize, samplewidth=2)
    ws2 = WaveSynth(samplerate=params.norm_osc_blocksize, samplewidth=2)
    ncols = 4
    nrows = 3
    freq = 2
    dur = 1.0
    harmonics = [(n, 1 / n) for n in range(3, 5 * 2, 2)]
    fm = FastSine(1, amplitude=0, bias=0, samplerate=ws.samplerate)
    waveforms = [
        ('sine', ws.sine(freq, dur).get_frame_array()),
        ('square', ws.square(freq, dur).get_frame_array()),
        ('square_h', ws.square_h(freq, dur, num_harmonics=5).get_frame_array()),
        ('triangle', ws.triangle(freq, dur).get_frame_array()),
        ('sawtooth', ws.sawtooth(freq, dur).get_frame_array()),
        ('sawtooth_h', ws.sawtooth_h(freq, dur, num_harmonics=5).get_frame_array()),
        ('pulse', ws.pulse(freq, dur).get_frame_array()),
        ('harmonics', ws.harmonics(freq, dur, harmonics=harmonics).get_frame_array()),
        ('white_noise', ws2.white_noise(50, dur).get_frame_array()),
        ('linear', get_data(Linear(20, 0.2, max_value=100, samplerate=ws.samplerate))),
        ('W2-pointy', ws.pointy(freq, dur, fm_lfo=fm).get_frame_array()),
        ('W3-semicircle', ws.semicircle(freq, dur, fm_lfo=fm).get_frame_array())
    ]
    plot.figure(1, figsize=(16, 10))
    plot.suptitle("waveforms (2 cycles)")
    for i, (waveformname, values) in enumerate(waveforms, start=1):
        ax = plot.subplot(nrows, ncols, i)
        ax.set_yticklabels([])
        ax.set_xticklabels([])
        plot.title(waveformname)
        plot.grid(True)
        plot.plot(values)
    plot.subplots_adjust(hspace=0.5, wspace=0.5, top=0.90, bottom=0.1, left=0.05, right=0.95)
    plot.show()


if __name__ == "__main__":
    check_waveforms()
    plot_waveforms()
