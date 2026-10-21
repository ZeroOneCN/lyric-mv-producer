"""Shift the spectral envelope of a vocal without moving F0.

Keeps every STFT bin's phase and only reweights magnitudes by the ratio of a
cepstrally smoothed envelope warped along frequency. This changes perceived
vocal-tract size while preserving melody and timing.
"""
import argparse
import numpy as np
import soundfile as sf
from scipy.signal import get_window, resample_poly

N_FFT = 2048
HOP = 512
LIFTER_MS = 2.2
MAX_GAIN_DB = 10.0


def stft(x: np.ndarray):
    win = get_window("hann", N_FFT, fftbins=True)
    pad = N_FFT
    xp = np.pad(x, (pad, pad), mode="reflect")
    n_frames = 1 + (len(xp) - N_FFT) // HOP
    frames = np.lib.stride_tricks.as_strided(
        xp,
        shape=(n_frames, N_FFT),
        strides=(xp.strides[0] * HOP, xp.strides[0]),
        writeable=False,
    )
    return np.fft.rfft(frames * win, axis=1), win, pad


def istft(X: np.ndarray, win: np.ndarray, pad: int, length: int):
    frames = np.fft.irfft(X, n=N_FFT, axis=1) * win
    out = np.zeros((len(frames) - 1) * HOP + N_FFT, dtype=np.float64)
    wsum = np.zeros_like(out)
    w2 = win * win
    for i, frame in enumerate(frames):
        a = i * HOP
        out[a:a + N_FFT] += frame
        wsum[a:a + N_FFT] += w2
    out /= np.maximum(wsum, 1e-9)
    return out[pad:pad + length]


def envelope(log_mag: np.ndarray, sr: int):
    cep = np.fft.irfft(log_mag, n=N_FFT, axis=1)
    q = max(1, int(LIFTER_MS / 1000.0 * sr))
    cep[:, q:-q] = 0.0
    return np.fft.rfft(cep, axis=1).real


def shift_channel(x: np.ndarray, sr: int, alpha: float, strength: float):
    X, win, pad = stft(x)
    mag = np.abs(X)
    phase = X / np.maximum(mag, 1e-12)
    env = np.exp(envelope(np.log(mag + 1e-9), sr))
    freqs = np.fft.rfftfreq(N_FFT, 1.0 / sr)
    src = freqs / alpha
    warped = np.empty_like(env)
    for i in range(len(env)):
        warped[i] = np.interp(src, freqs, env[i], left=env[i, 0], right=env[i, -1])
    gain = warped / np.maximum(env, 1e-9)
    lim = 10 ** (MAX_GAIN_DB / 20.0)
    gain = np.clip(gain, 1.0 / lim, lim)
    gain = 1.0 + strength * (gain - 1.0)
    Y = (mag * gain) * phase
    y = istft(Y, win, pad, len(x))
    rms_in = np.sqrt(np.mean(x * x) + 1e-12)
    rms_out = np.sqrt(np.mean(y * y) + 1e-12)
    return y * (rms_in / rms_out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--alpha", type=float, default=1.12,
                    help="formant scale, 1.0 = unchanged, 1.12 = +12%%")
    ap.add_argument("--strength", type=float, default=1.0)
    ap.add_argument("--sr", type=int, default=48000)
    args = ap.parse_args()

    audio, sr = sf.read(args.src, always_2d=True)
    if sr != args.sr:
        audio = resample_poly(audio, args.sr, sr, axis=0)
        sr = args.sr
    out = np.empty_like(audio)
    for ch in range(audio.shape[1]):
        out[:, ch] = shift_channel(audio[:, ch], sr, args.alpha, args.strength)
    peak = np.max(np.abs(out))
    if peak > 0.99:
        out *= 0.99 / peak
    sf.write(args.dst, out, sr, subtype="PCM_24")
    print(f"{args.dst}: {len(out)/sr:.3f}s, alpha={args.alpha}, strength={args.strength}, peak={20*np.log10(peak+1e-12):.1f} dBFS")


if __name__ == "__main__":
    main()
