"""Zwei synthetische Ersatz-Musikstücke (numpy + ffmpeg) fürs Horus-Pitch-Video.

gen-musik-spannung-1: 110 BPM, 24 Takte (52,4 s), D-Moll, baut sich in 4 Stufen auf, endet hart.
gen-musik-aufloesung-1: 15 s, D-Dur-Fläche mit Glockenmelodie, warm, langsam ausklingend.
"""
import sys
import numpy as np

sys.path.insert(0, sys.argv[2])
import synth_sfx as s  # noqa: E402  (nutzt svf, reverb, bell, save)

SR = s.SR
s.OUT = sys.argv[1]
rng = np.random.default_rng(611)

BPM = 110
BEAT = 60 / BPM
BAR = 4 * BEAT
BARS = 24
N = int(round(BARS * BAR * SR))


def place(buf, sig, at_s, gain=1.0):
    p = int(round(at_s * SR))
    e = min(len(buf), p + len(sig))
    if p < len(buf):
        buf[p:e] += gain * sig[: e - p]


def saw_note(f, d, cutoff, det=0.006):
    tt = np.arange(int(d * SR)) / SR
    x = np.zeros_like(tt)
    for dd in (-det, det):
        ph = f * (1 + dd) * tt
        x += 2 * (ph % 1) - 1
    env = (1 - np.exp(-tt / 0.004)) * np.exp(-tt / (d * 0.45))
    return s.svf(x * env, cutoff, 1.4, "lp")


def kick():
    d = 0.45
    return np.tanh(2.0 * s.glide(140, 48, 0.06, d) * s.env_exp(d, 0.11))


def hat(d=0.05):
    n = int(d * SR)
    return s.svf(rng.standard_normal(n), 8000, 1.2) * np.exp(-np.arange(n) / (0.008 * SR))


def snare():
    d = 0.25
    n = int(d * SR)
    tt = np.arange(n) / SR
    body = np.sin(2 * np.pi * 190 * tt) * np.exp(-tt / 0.03)
    nz = s.svf(rng.standard_normal(n), 2500, 0.8) * np.exp(-tt / 0.06)
    return 0.5 * body + nz / np.max(np.abs(nz))


def spannung():
    tt = np.arange(N) / SR
    prog = tt / tt[-1]
    out = np.zeros(N)

    # 1) Drone auf D1/D2, Filter öffnet sich über die ganze Länge
    drone = np.zeros(N)
    for f, a in ((36.71, 1.0), (73.42, 0.5), (110.0, 0.2)):
        for dd in (-0.003, 0.003):
            ph = f * (1 + dd) * tt
            drone += a * (2 * (ph % 1) - 1)
    drone = s.svf(drone, 120 + 900 * prog ** 2, 0.9, "lp")
    out += 0.35 * drone / np.max(np.abs(drone)) * (0.4 + 0.6 * prog)

    # 2) Bass-Ostinato in Achteln (ab Takt 1), D-D-D-F-D-D-C-D
    pattern = [73.42, 73.42, 73.42, 87.31, 73.42, 73.42, 65.41, 73.42]
    bass = np.zeros(N)
    for bar in range(BARS):
        st = bar / BARS
        for i, f in enumerate(pattern):
            note = saw_note(f, BEAT / 2 * 0.9, 300 + 2200 * st ** 1.5)
            place(bass, note, bar * BAR + i * BEAT / 2, 0.35 + 0.65 * st)
    out += 0.45 * bass / np.max(np.abs(bass))

    # 3) Kick auf Vierteln ab Takt 5
    k = kick()
    perc = np.zeros(N)
    for bar in range(4, BARS):
        for b in range(4):
            place(perc, k, bar * BAR + b * BEAT, 0.8 + 0.2 * bar / BARS)
    # 4) Offbeat-Hats ab Takt 9, Sechzehntel ab Takt 17
    for bar in range(8, BARS):
        for b in range(4):
            place(perc, hat(), bar * BAR + b * BEAT + BEAT / 2, 0.25)
            if bar >= 16:
                for q in (1, 3):
                    place(perc, hat(0.03), bar * BAR + b * BEAT + q * BEAT / 4, 0.15)
    # 5) Snare auf 2 und 4 ab Takt 13, ab Takt 23 Snare-Wirbel in Sechzehnteln
    sn = snare()
    for bar in range(12, BARS):
        if bar >= 22:
            for q in range(16):
                place(perc, sn, bar * BAR + q * BEAT / 4, 0.25 + 0.5 * q / 16)
        else:
            for b in (1, 3):
                place(perc, sn, bar * BAR + b * BEAT, 0.6)
    out += 0.6 * perc / np.max(np.abs(perc))

    # 6) Hohes Arpeggio in Sechzehnteln ab Takt 17 (D-F-A-C)
    arp = np.zeros(N)
    notes = [587.33, 698.46, 880.0, 1046.5]
    for bar in range(16, BARS):
        for q in range(16):
            n = saw_note(notes[q % 4], BEAT / 4 * 0.8, 3000, 0.003)
            place(arp, n, bar * BAR + q * BEAT / 4, 0.5 + 0.5 * (bar - 16) / 8)
    out += 0.18 * arp / np.max(np.abs(arp))

    # Harter Schluss: letzte Zählzeit endet abrupt (nur 5 ms Ausblendung gegen Knacken)
    out = out * (0.3 + 0.7 * prog ** 1.3)  # Gesamtlautstaerke steigt ueber die ganze Laenge
    out = np.tanh(1.6 * out)
    st = s.stereo(out)
    st[:, 0] += 0.05 * np.roll(out, 240)  # etwas Breite
    st[:, 1] += 0.05 * np.roll(out, 410)
    s.save("gen-musik-spannung-1.wav", st, -3.0)


def aufloesung():
    d = 15.0
    tt = np.arange(int(d * SR)) / SR
    pad = np.zeros_like(tt)
    for f in (146.83, 220.0, 293.66, 369.99, 440.0):  # D-Dur
        for dd in (-0.004, 0.0, 0.004):
            ph = 2 * np.pi * f * (1 + dd) * tt + rng.uniform(0, 6.28)
            pad += np.sin(ph) + 0.25 * np.sin(2 * ph)
    env = np.minimum(tt / 2.5, 1.0) * np.where(tt > 10.0, np.exp(-(tt - 10.0) / 1.8), 1.0)
    pad = s.onepole_lp(pad * env, 1500)
    pad /= np.max(np.abs(pad))
    mel = np.zeros_like(tt)
    for at, f in ((1.5, 880.0), (3.5, 739.99), (5.5, 587.33), (8.0, 659.26), (9.5, 587.33)):
        place(mel, s.bell(f, 4.0, 1.2, ((1, 1.0), (2.0, 0.15), (3.0, 0.04))), at, 0.5)
    x = 0.7 * pad + 0.35 * mel
    s.save("gen-musik-aufloesung-1.wav", s.reverb(x, 3.5, 0.35, seed=77), -3.0)


if __name__ == "__main__":
    spannung()
    aufloesung()
