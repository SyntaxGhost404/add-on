"""Original synthesized sounds (numpy) encoded to Ogg Vorbis with ffmpeg."""
import os
import subprocess
import tempfile
import wave

import numpy as np

SR = 44100


def _env(n, attack, release):
    e = np.ones(n)
    a = int(attack * SR)
    r = int(release * SR)
    if a:
        e[:a] = np.linspace(0, 1, a) ** 1.5
    if r:
        e[-r:] = np.linspace(1, 0, r) ** 1.5
    return e


def _reverb(x, seconds=1.2, mix=0.35, seed=1):
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    ir = rng.standard_normal(n) * np.exp(-np.linspace(0, 6, n))
    ir /= np.sqrt(np.sum(ir ** 2))
    wet = np.convolve(x, ir)[:len(x) + n // 2]
    out = np.zeros(len(wet))
    out[:len(x)] += x * (1 - mix)
    out += wet * mix
    return out


def _formant_weight(freq):
    # crude "ah" vowel: formants near 700, 1220, 2600 Hz
    w = 0.0
    for f, bw, g in ((700, 130, 1.0), (1220, 180, 0.6), (2600, 260, 0.25)):
        w += g * np.exp(-((freq - f) / bw) ** 2)
    return 0.15 + w


def choir_drone(duration=4.5):
    n = int(duration * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    rng = np.random.default_rng(7)
    for base in (110.0, 164.81, 220.0, 261.63):
        for detune in (-0.004, 0.0, 0.0035):
            f0 = base * (1 + detune)
            vib = 1 + 0.004 * np.sin(2 * np.pi * (4.6 + rng.random()) * t + rng.random() * 6)
            phase = 2 * np.pi * np.cumsum(f0 * vib) / SR
            for h in range(1, 14):
                fh = f0 * h
                if fh > 5000:
                    break
                out += _formant_weight(fh) * np.sin(h * phase) / h ** 0.7
    breath = np.convolve(rng.standard_normal(n), np.ones(40) / 40, mode='same') * 0.02
    out = (out / np.max(np.abs(out)) + breath) * _env(n, 1.4, 1.8)
    return _reverb(out, 1.6, 0.4, 3)


def glyph_chime(duration=2.6):
    n = int(duration * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for f, amp, decay in ((659.25, 1.0, 2.2), (987.77, 0.55, 3.0), (1318.5, 0.3, 4.0), (1975.5, 0.12, 6.0)):
        idx = 2.2 * np.exp(-t * 3)
        out += amp * np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * 1.41 * t)) * np.exp(-t * decay)
    out *= _env(n, 0.004, 0.3)
    return _reverb(out, 1.4, 0.3, 4)


def low_hum(duration=3.4):
    n = int(duration * SR)
    t = np.arange(n) / SR
    out = (np.sin(2 * np.pi * 55 * t) + 0.8 * np.sin(2 * np.pi * 55.7 * t) + 0.45 * np.sin(2 * np.pi * 82.4 * t)
           + 0.2 * np.sin(2 * np.pi * 110.3 * t))
    out *= 0.6 + 0.4 * np.sin(2 * np.pi * 0.7 * t)
    rng = np.random.default_rng(11)
    shimmer = np.convolve(rng.standard_normal(n), np.hanning(64), mode='same')
    out += 0.05 * shimmer * np.sin(2 * np.pi * 880 * t)
    out *= _env(n, 0.9, 1.4)
    return _reverb(out, 1.0, 0.25, 5)


def whisper(duration=2.4, seed=21):
    n = int(duration * SR)
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(n)
    # band-limit roughly to 1.2-4.5 kHz with a difference of moving averages
    lo = np.convolve(noise, np.ones(9) / 9, mode='same')
    hi = np.convolve(noise, np.ones(36) / 36, mode='same')
    band = lo - hi
    env = np.zeros(n)
    pos = int(0.1 * SR)
    while pos < n - int(0.3 * SR):
        ln = int(rng.uniform(0.08, 0.28) * SR)
        seg = np.hanning(ln) * rng.uniform(0.4, 1.0)
        env[pos:pos + ln] += seg[:max(0, min(ln, n - pos))]
        pos += ln + int(rng.uniform(0.02, 0.12) * SR)
    t = np.arange(n) / SR
    out = band * env * (1 + 0.3 * np.sin(2 * np.pi * 3.1 * t))
    return _reverb(out, 1.3, 0.45, seed)


SOUNDS = {
    'choir_drone': choir_drone,
    'glyph_chime': glyph_chime,
    'low_hum': low_hum,
    'whisper1': lambda: whisper(2.4, 21),
    'whisper2': lambda: whisper(2.0, 22),
}


def write_ogg(samples, path):
    samples = samples / (np.max(np.abs(samples)) + 1e-9) * 0.7
    pcm = (samples * 32767).astype(np.int16)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, 'x.wav')
        with wave.open(wav, 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav, '-c:a', 'libvorbis', '-q:a', '4',
                        '-ac', '1', '-ar', str(SR), '-map_metadata', '-1', '-fflags', '+bitexact',
                        '-flags:a', '+bitexact', path], check=True)
