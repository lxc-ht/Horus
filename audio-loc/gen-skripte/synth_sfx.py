"""Synthetisiert die SFX fürs Horus-Pitch-Video (numpy + ffmpeg, 48 kHz, 24 bit WAV)."""
import subprocess
import sys
import numpy as np

SR = 48000
OUT = sys.argv[1]
rng = np.random.default_rng(6112026)


def t(d):
    return np.arange(int(d * SR)) / SR


def env_exp(d, tau):
    return np.exp(-t(d) / tau)


def svf(x, fc, q=0.7, mode="bp"):
    """State-variable-Filter, fc darf ein Array (zeitvariabel) sein."""
    fc = np.broadcast_to(np.asarray(fc, dtype=float), x.shape)
    f = 2 * np.sin(np.pi * np.clip(fc, 10, SR / 6) / SR)
    dmp = 1.0 / q
    low = band = 0.0
    out = np.empty_like(x)
    for i in range(len(x)):
        high = x[i] - low - dmp * band
        band += f[i] * high
        low += f[i] * band
        out[i] = band if mode == "bp" else (low if mode == "lp" else high)
    return out


def onepole_lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    s = 0.0
    for i in range(len(x)):
        s = (1 - a) * x[i] + a * s
        y[i] = s
    return y


def reverb(x, decay=1.5, mix=0.25, seed=1):
    r = np.random.default_rng(seed)
    x = fade(x, 0.0, 0.05)  # trockenes Ende weich auslaufen lassen
    n = int(decay * SR)
    ir_l = r.standard_normal(n) * np.exp(-np.arange(n) / (decay * SR / 6.9))
    ir_r = r.standard_normal(n) * np.exp(-np.arange(n) / (decay * SR / 6.9))
    ir_l[: int(0.01 * SR)] = 0
    ir_r[: int(0.013 * SR)] = 0
    L = len(x) + n
    nfft = 1 << (L - 1).bit_length()
    X = np.fft.rfft(x, nfft)
    wl = np.fft.irfft(X * np.fft.rfft(ir_l, nfft), nfft)[:L]
    wr = np.fft.irfft(X * np.fft.rfft(ir_r, nfft), nfft)[:L]
    wl /= np.max(np.abs(wl)) + 1e-9
    wr /= np.max(np.abs(wr)) + 1e-9
    dry = np.concatenate([x, np.zeros(n)]) / (np.max(np.abs(x)) + 1e-9)
    return np.stack([(1 - mix) * dry + mix * wl, (1 - mix) * dry + mix * wr], axis=1)


def stereo(x, pan=0.0):
    if x.ndim == 2:
        return x
    l = np.cos((pan + 1) * np.pi / 4)
    r = np.sin((pan + 1) * np.pi / 4)
    return np.stack([x * l, x * r], axis=1)


def fade(x, fin=0.002, fout=0.01):
    x = x.copy()
    a, b = int(fin * SR), int(fout * SR)
    if a:
        x[:a] *= np.linspace(0, 1, a)[:, None] if x.ndim == 2 else np.linspace(0, 1, a)
    if b:
        x[-b:] *= np.linspace(1, 0, b)[:, None] if x.ndim == 2 else np.linspace(1, 0, b)
    return x


def save(name, x, peak_db=-3.0):
    x = stereo(x)
    x = fade(x)
    x = x / (np.max(np.abs(x)) + 1e-12) * 10 ** (peak_db / 20)
    raw = x.astype("<f4").tobytes()
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2",
         "-i", "-", "-c:a", "pcm_s24le", f"{OUT}/{name}"],
        input=raw, check=True)
    print(name, f"{len(x)/SR:.2f}s")


def sweep_sine(f0, f1, d, curve="exp"):
    tt = t(d)
    if curve == "exp":
        f = f0 * (f1 / f0) ** (tt / d)
    else:
        f = f0 + (f1 - f0) * tt / d
    return np.sin(2 * np.pi * np.cumsum(f) / SR), f


def glide(f0, f1, dglide, d):
    """Abfallende Frequenz, danach konstant – phasenstetig (kein Knack an der Naht)."""
    n1 = int(dglide * SR)
    n = int(d * SR)
    f = np.full(n, float(f1))
    f[:n1] = f0 * (f1 / f0) ** (np.arange(n1) / n1)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def noise(d):
    return rng.standard_normal(int(d * SR))


# ---------- hit ----------
def hit1():
    d = 0.7
    s = glide(160, 45, 0.08, d) * env_exp(d, 0.12)
    click = svf(noise(d), 2500, 1.0) * env_exp(d, 0.004)
    x = np.tanh(2.5 * (s + 0.4 * click))
    save("gen-sfx-hit-1.wav", x)


def hit2():
    d = 1.0
    s, _ = sweep_sine(110, 32, d)
    s *= env_exp(d, 0.25)
    slam = svf(noise(d), np.linspace(900, 150, int(d * SR)), 0.8, "lp") * env_exp(d, 0.05)
    x = np.tanh(1.8 * (s + 0.9 * slam / (np.max(np.abs(slam)) + 1e-9)))
    x = reverb(x, 0.6, 0.12, seed=2)
    save("gen-sfx-hit-2.wav", x)


# ---------- whoosh ----------
def whoosh(name, d, f0, fpeak, peak_at, q, seed_pan):
    n = int(d * SR)
    tt = np.linspace(0, 1, n)
    fc = np.where(tt < peak_at, f0 + (fpeak - f0) * (tt / peak_at) ** 2,
                  fpeak - (fpeak - f0) * ((tt - peak_at) / (1 - peak_at)))
    amp = np.where(tt < peak_at, (tt / peak_at) ** 2, ((1 - tt) / (1 - peak_at)) ** 1.5)
    x = svf(noise(d), fc, q) * amp
    pan = np.linspace(-0.8, 0.8, n) * seed_pan
    l = np.cos((pan + 1) * np.pi / 4)
    r = np.sin((pan + 1) * np.pi / 4)
    st = np.stack([x * l, x * r], axis=1)
    save(name, st)


# ---------- riser ----------
def riser1():
    d = 3.0
    n = int(d * SR)
    tt = np.linspace(0, 1, n)
    nz = svf(noise(d), 300 * (8000 / 300) ** tt, 1.5) * tt ** 2
    tone, _ = sweep_sine(110, 880, d)
    tone2, _ = sweep_sine(110 * 1.5, 880 * 1.5, d)
    x = 0.6 * nz / np.max(np.abs(nz)) + 0.4 * (tone + 0.5 * tone2) * tt ** 2.5
    x = reverb(x, 1.2, 0.25, seed=3)
    save("gen-sfx-riser-1.wav", x)


def riser2():
    d = 4.0
    n = int(d * SR)
    tt = np.linspace(0, 1, n)
    x = np.zeros(n)
    for det in (-0.012, -0.004, 0.0, 0.006, 0.013):
        f = 55 * (1 + det) * (440 / 55) ** (tt ** 1.6)
        ph = np.cumsum(f) / SR
        x += 2 * (ph % 1) - 1  # Saegezahn
    x = svf(x, 200 + 6000 * tt ** 2, 0.9, "lp")
    trem = 0.75 + 0.25 * np.sin(2 * np.pi * np.cumsum(2 + 14 * tt ** 2) / SR)
    x = x * tt ** 2 * trem
    x = reverb(x, 1.0, 0.2, seed=4)
    save("gen-sfx-riser-2.wav", x)


# ---------- boom ----------
def boom1():
    d = 3.0
    s = glide(120, 28, 1.2, d) * env_exp(d, 0.9)
    x = np.tanh(1.5 * s)
    save("gen-sfx-boom-1.wav", x)


def boom2():
    d = 4.0
    s = glide(70, 24, 2.5, d) * env_exp(d, 1.2)
    imp = svf(noise(d), 180, 0.7, "lp") * env_exp(d, 0.15)
    x = np.tanh(2.0 * (s + 0.8 * imp / np.max(np.abs(imp))))
    x = reverb(x, 2.5, 0.3, seed=5)
    save("gen-sfx-boom-2.wav", x)


# ---------- tippen ----------
def key_click(r, bright=1.0):
    d = 0.06
    n = int(d * SR)
    nz = r.standard_normal(n)
    c = svf(nz, r.uniform(2500, 4500) * bright, 3.0) * np.exp(-np.arange(n) / (0.004 * SR))
    thock = np.sin(2 * np.pi * r.uniform(180, 260) * np.arange(n) / SR) * np.exp(-np.arange(n) / (0.012 * SR))
    return c + 0.5 * thock


def typing(name, d, seed, mean_gap, bright, wpm_burst):
    r = np.random.default_rng(seed)
    n = int(d * SR)
    x = np.zeros(n + SR)
    pos = int(0.2 * SR)
    end_typing = int((d - 1.0) * SR)
    count = 0
    while pos < end_typing:
        k = key_click(r, bright) * r.uniform(0.5, 1.0)
        x[pos:pos + len(k)] += k
        count += 1
        gap = r.gamma(2.0, mean_gap / 2.0)
        if count % wpm_burst == 0:
            gap += r.uniform(0.15, 0.35)  # Wortpause
        pos += int(gap * SR)
    # Einfuegen: Cmd (leiser) + V, dann Maus-/Senden-Klick
    pos = end_typing + int(0.35 * SR)
    for amp in (0.6, 1.0):
        k = key_click(r, bright * 0.8) * amp
        x[pos:pos + len(k)] += k
        pos += int(0.07 * SR)
    pos += int(0.4 * SR)
    m = 0.07
    mn = int(m * SR)
    click = svf(r.standard_normal(mn), 5200, 6.0) * np.exp(-np.arange(mn) / (0.0025 * SR))
    x[pos:pos + mn] += 1.6 * click
    x = x[:n]
    x = reverb(x, 0.35, 0.08, seed=seed)
    save(name, x, -6.0)


# ---------- senden ----------
def senden1():
    d = 0.7
    n = int(d * SR)
    tt = np.linspace(0, 1, n)
    nz = svf(noise(d), 600 * (9000 / 600) ** tt, 2.0) * np.sin(np.pi * tt) ** 2
    blip, _ = sweep_sine(600, 2400, d)
    x = nz / np.max(np.abs(nz)) + 0.25 * blip * np.sin(np.pi * tt) ** 3
    st = np.stack([x * np.cos((tt * 1.4 - 0.7 + 1) * np.pi / 4), x * np.sin((tt * 1.4 - 0.7 + 1) * np.pi / 4)], 1)
    save("gen-sfx-senden-1.wav", reverb(st[:, 0] + st[:, 1], 0.5, 0.15, seed=7) if False else st)


def senden2():
    d = 1.1
    n = int(d * SR)
    tt = np.linspace(0, 1, n)
    amp = np.where(tt < 0.3, (tt / 0.3) ** 2, np.exp(-(tt - 0.3) * 6))
    nz = svf(noise(d), 400 + 5000 * np.sin(np.pi * np.minimum(tt / 0.6, 1) / 2), 1.2) * amp
    tone, _ = sweep_sine(300, 1800, d)
    x = nz / np.max(np.abs(nz)) + 0.2 * tone * amp
    x = reverb(x, 0.9, 0.25, seed=8)
    save("gen-sfx-senden-2.wav", x)


# ---------- glitch ----------
def glitch1():
    d = 2.0
    n = int(d * SR)
    x = np.zeros(n)
    pos = 0
    r = np.random.default_rng(11)
    while pos < n:
        seg = int(r.uniform(0.01, 0.09) * SR)
        kind = r.integers(0, 4)
        tt = np.arange(seg) / SR
        if kind == 0:
            s = r.standard_normal(seg)
            step = r.integers(4, 40)
            s = np.repeat(s[::step], step)[:seg]  # Sample-and-hold
        elif kind == 1:
            s = np.sign(np.sin(2 * np.pi * r.uniform(200, 3000) * tt))
        elif kind == 2:
            s = np.zeros(seg)
        else:
            s = np.round(r.standard_normal(seg) * 2) / 2
        x[pos:pos + seg] = s[: n - pos] * r.uniform(0.3, 1.0)
        pos += seg
    x = np.round(x * 8) / 8  # Bitcrush
    st = np.stack([x, np.roll(x, 37)], 1)
    save("gen-sfx-glitch-1.wav", st, -6.0)


def glitch2():
    d = 3.0
    n = int(d * SR)
    tt = t(d)
    r = np.random.default_rng(12)
    base = svf(r.standard_normal(n), 3000, 0.6) * 0.3
    data = np.zeros(n)
    bits = r.integers(0, 2, int(d * 300))
    sym = int(SR / 300)
    for i, b in enumerate(bits):
        a, e = i * sym, min((i + 1) * sym, n)
        f = 1200 if b else 2200  # FSK-artig
        data[a:e] = np.sin(2 * np.pi * f * tt[a:e])
    gate = np.repeat(r.random(int(d * 25)) > 0.35, int(SR / 25))[:n]
    gate = np.pad(gate, (0, n - len(gate))).astype(float)
    x = (base + 0.5 * data) * gate
    hum = 0.15 * np.sin(2 * np.pi * 60 * tt)
    x = np.round((x + hum) * 12) / 12
    save("gen-sfx-glitch-2.wav", stereo(x, 0.0), -6.0)


# ---------- puls ----------
def heartbeat(bpm, beats, name):
    period = 60 / bpm
    d = period * beats
    n = int(round(d * SR))
    x = np.zeros(n + SR)
    def thump(f0, dur, a):
        tt = t(dur)
        f = f0 * np.exp(-tt * 8) + 38
        return a * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / (dur / 4))
    for b in range(beats):
        p = int(b * period * SR)
        lub = thump(70, 0.18, 1.0)
        dub = thump(85, 0.14, 0.7)
        x[p:p + len(lub)] += lub
        q = p + int(0.28 * SR)
        x[q:q + len(dub)] += dub
    # Ueberhang an den Anfang falten -> nahtloser Loop
    x[: SR] += x[n: n + SR]
    x = x[:n]
    x = onepole_lp(np.tanh(1.5 * x), 400)
    x = stereo(x)
    x = x / np.max(np.abs(x)) * 10 ** (-3 / 20)
    raw = x.astype("<f4").tobytes()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2",
                    "-i", "-", "-c:a", "pcm_s24le", f"{OUT}/{name}"], input=raw, check=True)
    print(name, f"{n/SR:.2f}s loop")


def puls2():
    bpm, beats = 60, 8
    period = 60 / bpm
    n = int(period * beats * SR)
    x = np.zeros(n + SR)
    for b in range(beats):
        p = int(b * period * SR)
        tt = t(0.9)
        s = np.sin(2 * np.pi * 42 * tt) * (1 - np.exp(-tt / 0.01)) * np.exp(-tt / 0.3)
        s += 0.3 * np.sin(2 * np.pi * 84 * tt) * np.exp(-tt / 0.1)
        x[p:p + len(s)] += s
    x[:SR] += x[n:n + SR]
    x = x[:n]
    x = stereo(np.tanh(1.3 * x))
    x = x / np.max(np.abs(x)) * 10 ** (-3 / 20)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2",
                    "-i", "-", "-c:a", "pcm_s24le", f"{OUT}/gen-sfx-puls-2.wav"],
                   input=x.astype("<f4").tobytes(), check=True)
    print("gen-sfx-puls-2.wav", f"{n/SR:.2f}s loop")


# ---------- tick ----------
def tick_single(r, f=3200, wood=False):
    d = 0.03
    n = int(d * SR)
    if wood:
        tt = np.arange(n) / SR
        return (np.sin(2 * np.pi * 1800 * tt) + 0.5 * np.sin(2 * np.pi * 2900 * tt)) * np.exp(-tt / 0.004)
    return svf(r.standard_normal(n), f, 8.0) * np.exp(-np.arange(n) / (0.0015 * SR))


def tick_seq(name, wood, seed):
    r = np.random.default_rng(seed)
    # erst ein einzelner Tick, dann ein beschleunigender Zaehler (2,5 s), dann Halt
    d = 4.0
    n = int(d * SR)
    x = np.zeros(n)
    k = tick_single(r, wood=wood)
    x[int(0.1 * SR): int(0.1 * SR) + len(k)] += k
    pos = 0.8
    gap = 0.18
    while pos < 3.3:
        k = tick_single(r, f=r.uniform(2900, 3400), wood=wood)
        p = int(pos * SR)
        x[p:p + len(k)] += k
        pos += gap
        gap = max(0.035, gap * 0.9)
    save(name, x, -6.0)


# ---------- ping ----------
def bell(f, d, tau, partials=((1, 1.0), (2.76, 0.4), (5.4, 0.15))):
    tt = t(d)
    s = np.zeros_like(tt)
    for m, a in partials:
        s += a * np.sin(2 * np.pi * f * m * tt) * np.exp(-tt / (tau / m ** 0.7))
    return s * (1 - np.exp(-tt / 0.002))


def ping1():
    d = 1.6
    x = np.zeros(int(d * SR))
    a = bell(1046.5, 1.2, 0.35, ((1, 1.0), (2.0, 0.2), (3.0, 0.05)))
    b = bell(1568.0, 1.2, 0.45, ((1, 1.0), (2.0, 0.2), (3.0, 0.05)))
    x[: len(a)] += a
    o = int(0.11 * SR)
    x[o:o + len(b)] += 0.9 * b
    save("gen-sfx-ping-1.wav", reverb(x, 0.8, 0.2, seed=21))


def ping2():
    d = 1.8
    tt = t(d)
    mod = 1.5 * np.exp(-tt / 0.08) * np.sin(2 * np.pi * 1320 * 3.5 * tt)
    x = np.sin(2 * np.pi * 1320 * tt + mod) * np.exp(-tt / 0.4) * (1 - np.exp(-tt / 0.003))
    save("gen-sfx-ping-2.wav", reverb(x, 1.0, 0.25, seed=22))


# ---------- logo ----------
def logo1():
    # Klangschale: unharmonische Teiltoene, je zwei leicht verstimmt (Schwebung)
    d = 9.0
    tt = t(d)
    f0 = 220.0
    x = np.zeros_like(tt)
    for m, a, tau in ((1.0, 1.0, 4.5), (2.71, 0.5, 3.0), (5.1, 0.25, 1.8), (8.2, 0.1, 1.0)):
        for det in (-0.6, 0.6):
            x += a * np.sin(2 * np.pi * (f0 * m + det) * tt) * np.exp(-tt / tau)
    strike = svf(noise(d), 1800, 1.0) * np.exp(-tt / 0.01) * 0.3
    x = (x + strike) * (1 - np.exp(-tt / 0.004))
    save("gen-sfx-logo-1.wav", reverb(x, 3.0, 0.3, seed=31))


def logo2():
    # Warmes Pad: D-Dur add9 (D3 A3 D4 E4 F#4), langsamer Anstieg
    d = 12.0
    tt = t(d)
    freqs = (146.83, 220.0, 293.66, 329.63, 369.99)
    x = np.zeros_like(tt)
    for f in freqs:
        for det in (-0.004, 0.0, 0.005):
            ph = 2 * np.pi * f * (1 + det) * tt + rng.uniform(0, 6.28)
            x += np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)
    env = np.minimum(tt / 3.0, 1.0) * np.where(tt > 8.0, np.exp(-(tt - 8.0) / 1.3), 1.0)
    x = onepole_lp(x * env, 1800)
    save("gen-sfx-logo-2.wav", reverb(x, 3.5, 0.35, seed=32))


if __name__ == "__main__":
    hit1(); hit2()
    whoosh("gen-sfx-whoosh-1.wav", 1.2, 250, 3500, 0.55, 1.2, 1)
    whoosh("gen-sfx-whoosh-2.wav", 0.6, 400, 6000, 0.35, 2.0, -1)
    riser1(); riser2()
    boom1(); boom2()
    typing("gen-sfx-tippen-1.wav", 5.0, 41, 0.11, 1.0, 5)
    typing("gen-sfx-tippen-2.wav", 4.0, 42, 0.085, 0.75, 7)
    senden1(); senden2()
    glitch1(); glitch2()
    heartbeat(72, 8, "gen-sfx-puls-1.wav")
    puls2()
    tick_seq("gen-sfx-tick-1.wav", False, 51)
    tick_seq("gen-sfx-tick-2.wav", True, 52)
    ping1(); ping2()
    logo1(); logo2()
