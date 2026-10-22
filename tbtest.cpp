// Golden-render check and timing for the voice: tbtest golden DIR | check DIR | time
#include "voice.h"
#include <chrono>
#include <complex>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <algorithm>
#include <string>
#include <vector>
using namespace tb303;

struct Scenario { const char *name; Controls c; int pattern; };

static std::vector<float> render(const Scenario &sc, double secs = 6)
{
	Voice v;
	v.prepare(48000);
	v.setControls(sc.c);
	const int n = int(secs * 48000), blk = 128, stepLen = 48000 / 8; // 16ths at 120 BPM
	std::vector<float> out(n);
	CpuLines l;
	unsigned trig = 0;
	int lastStep = -1;
	for (int p = 0; p < n; p += blk) {
		const int step = p / stepLen;
		if (step != lastStep) {
			lastStep = step;
			static const int notes[] = {36, 36, 48, 39, 36, 43, 46, 36, 41, 36, 48, 51, 36, 34, 36, 46};
			l.note = notes[step % 16] + (sc.pattern == 1 ? 12 : 0);
			l.accent = (step % 3 == 0);
			l.slide = (step % 5 == 2);
			l.gate = (step % 7 != 6);
			if (!l.slide)
				++trig;
			v.setLines(l, trig);
		}
		if (sc.pattern == 2) { // knob sweeps
			Controls c = sc.c;
			const double t = double(p) / n;
			c.cutoff = 0.5 + 0.5 * std::sin(6.28 * t * 3);
			c.envMod = t;
			c.resonance = 1 - t;
			c.square = step % 32 >= 16;
			v.setControls(c);
		}
		v.render(out.data() + p, std::min(blk, n - p));
	}
	return out;
}

static std::vector<Scenario> scenarios()
{
	auto C = [](double cut, double res, double env, double dec, double acc, bool sq) {
		Controls c; c.cutoff = cut; c.resonance = res; c.envMod = env; c.decay = dec; c.accent = acc; c.square = sq; return c; };
	return {
		{"saw_mid", C(0.5, 0.5, 0.5, 0.5, 0.5, false), 0},
		{"saw_fullres", C(0.4, 1.0, 0.7, 0.3, 1.0, false), 0},
		{"saw_closed", C(0.0, 0.8, 0.2, 0.8, 0.5, false), 0},
		{"saw_open", C(1.0, 0.0, 1.0, 1.0, 1.0, false), 1},
		{"sq_mid", C(0.5, 0.5, 0.5, 0.5, 0.5, true), 0},
		{"sq_fullres", C(0.6, 1.0, 0.9, 0.2, 1.0, true), 1},
		{"sweep", C(0.5, 0.5, 0.5, 0.5, 0.7, false), 2},
		{"saw_bright_res", C(0.85, 0.75, 0.8, 0.6, 0.8, false), 1},
		{"sq_bright_res", C(0.8, 0.9, 0.6, 0.4, 0.6, true), 0},
		{"saw_top_res", C(1.0, 1.0, 0.5, 0.5, 1.0, false), 1},
	};
}

static double db(double x) { return 20 * std::log10(x + 1e-30); }

// Spectral comparison (as Lemus's tools/compare/dinsync.py): sixth-octave band powers over
// 1024-sample Hann frames, hop 512; per frame the log-spectral distance weighted by each band's
// share of the golden frame, over frames within 60 dB of the loudest. Also frame level error.
static void fft(std::vector<std::complex<double>> &a)
{
	const size_t n = a.size();
	for (size_t i = 1, j = 0; i < n; ++i) {
		size_t bit = n >> 1;
		for (; j & bit; bit >>= 1)
			j ^= bit;
		j ^= bit;
		if (i < j)
			std::swap(a[i], a[j]);
	}
	for (size_t len = 2; len <= n; len <<= 1) {
		const std::complex<double> w = std::polar(1.0, -2 * M_PI / len);
		for (size_t i = 0; i < n; i += len) {
			std::complex<double> wk = 1;
			for (size_t k = 0; k < len / 2; ++k, wk *= w) {
				const auto u = a[i + k], v = a[i + k + len / 2] * wk;
				a[i + k] = u + v;
				a[i + k + len / 2] = u - v;
			}
		}
	}
}

static std::vector<std::vector<double>> bandFrames(const std::vector<float> &x, std::vector<double> &energy)
{
	const int n = 1024;
	std::vector<double> edges;
	for (int i = 0; i < 49; ++i)
		edges.push_back(40 * std::pow(2.0, i / 6.0));
	std::vector<std::vector<double>> out;
	for (size_t p = 0; p + n <= x.size(); p += n / 2) {
		std::vector<std::complex<double>> a(n);
		for (int i = 0; i < n; ++i)
			a[i] = x[p + i] * (0.5 - 0.5 * std::cos(2 * M_PI * i / (n - 1)));
		fft(a);
		std::vector<double> b(edges.size() - 1, 0.0);
		double e = 0;
		for (int k = 0; k <= n / 2; ++k) {
			const double f = k * 48000.0 / n, m = std::norm(a[k]);
			e += m;
			for (size_t q = 0; q + 1 < edges.size(); ++q)
				if (f >= edges[q] && f < edges[q + 1])
					b[q] += m;
		}
		out.push_back(b);
		energy.push_back(e);
	}
	return out;
}

// Returns mean LSD (dB); prints a line.
static double spectralCompare(const char *name, const std::vector<float> &ref, const std::vector<float> &out)
{
	std::vector<double> ea, eb;
	const auto a = bandFrames(ref, ea), b = bandFrames(out, eb);
	const double emax = *std::max_element(ea.begin(), ea.end());
	double sum = 0, worst = 0, lvl = 0, lvlMax = 0, worstRel = 0;
	int cnt = 0, worstFrame = 0;
	for (size_t f = 0; f < a.size(); ++f) {
		if (ea[f] < emax * 1e-6)
			continue;
		double tot = 0, acc = 0;
		for (double v : a[f])
			tot += v;
		for (size_t q = 0; q < a[f].size(); ++q) {
			const double d = 10 * std::log10((a[f][q] + 1e-12) / (b[f][q] + 1e-12));
			acc += a[f][q] / tot * d * d;
		}
		const double l = std::sqrt(acc), le = std::abs(10 * std::log10(ea[f] / eb[f]));
		sum += l;
		if (l > worst) {
			worst = l;
			worstFrame = int(f);
			worstRel = 10 * std::log10(ea[f] / emax);
		}
		lvl += le;
		lvlMax = std::max(lvlMax, le);
		++cnt;
	}
	printf("%-12s LSD mean %.3f dB  max %.3f (at %.2f s, %.0f dB under the loudest frame)  level mean %.3f dB  max %.3f\n", name, sum / cnt,
	       worst, worstFrame * 512 / 48000.0, -worstRel, lvl / cnt, lvlMax);
	return sum / cnt;
}

int main(int argc, char **argv)
{
	const std::string mode = argc > 1 ? argv[1] : "time";
	const std::string dir = argc > 2 ? argv[2] : ".";
	if (mode == "golden" || mode == "check") {
		int bad = 0;
		for (auto &sc : scenarios()) {
			auto out = render(sc);
			const std::string path = dir + "/" + sc.name + ".f32";
			if (mode == "golden") {
				FILE *f = fopen(path.c_str(), "wb");
				fwrite(out.data(), 4, out.size(), f);
				fclose(f);
				continue;
			}
			std::vector<float> ref(out.size());
			FILE *f = fopen(path.c_str(), "rb");
			if (!f || fread(ref.data(), 4, ref.size(), f) != ref.size()) { printf("%s: no golden\n", sc.name); return 2; }
			fclose(f);
			// A change of latency (oversampling, filter lengths) shifts the whole output: find
			// the lag (+/-64 samples) that best lines it up with the golden and compare there.
			int lag = 0;
			{
				double best = -1e300;
				const size_t span = std::min<size_t>(out.size() - 128, 96000);
				for (int l = -64; l <= 64; ++l) {
					double c = 0;
					for (size_t i = 64; i < span; ++i)
						c += double(ref[i]) * out[size_t(int(i) + l)];
					if (c > best) {
						best = c;
						lag = l;
					}
				}
				if (lag != 0) {
					std::vector<float> sh(out.size(), 0.0f);
					for (size_t i = 0; i < out.size(); ++i) {
						const long j = long(i) + lag;
						if (j >= 0 && j < long(out.size()))
							sh[i] = out[size_t(j)];
					}
					out = sh;
					printf("%-12s output lag %d samples\n", sc.name, lag);
				}
			}
			double peak = 0, se = 0, sr = 0;
			for (size_t i = 0; i < out.size(); ++i) {
				const double d = double(out[i]) - ref[i];
				peak = std::max(peak, std::abs(d));
				se += d * d;
				sr += double(ref[i]) * ref[i];
			}
			const double rel = db(std::sqrt(se / sr));
			printf("%-12s diff peak %7.1f dBFS  rms %7.1f dB rel\n", sc.name, db(peak), rel);
			const double lsd = spectralCompare(sc.name, ref, out);
			const bool ok = lsd < 0.1; // real unit vs its own retake: 2.2-2.5 dB
			bad += !ok;
			if (!ok)
				printf("  FAIL: mean LSD over 0.1 dB\n");
		}
		return bad ? 1 : 0;
	}
	if (mode == "alias") {
		// Inharmonic energy of a sustained, open-filter note (C5 and C6, saw and square): the
		// energy away from the harmonics, against the total, over 20 Hz-20 kHz.
		for (int sq = 0; sq < 2; ++sq)
			for (int note : {72, 84}) {
				Voice v;
				v.prepare(48000);
				Controls c;
				c.cutoff = 1;
				c.resonance = 0;
				c.envMod = 0;
				c.decay = 1;
				c.square = sq;
				v.setControls(c);
				CpuLines l;
				l.note = note;
				l.gate = true;
				v.setLines(l, 1);
				const int n = 1 << 16;
				std::vector<float> out(n + 24000);
				v.render(out.data(), int(out.size()));
				std::vector<std::complex<double>> a(n);
				for (int i = 0; i < n; ++i)
					a[i] = out[24000 + i] * (0.5 - 0.5 * std::cos(2 * M_PI * i / (n - 1)));
				fft(a);
				const double bin = 48000.0 / n;
				// f0: the probe's, refined to put the most energy on the harmonics.
				const auto split = [&](double f0, double &harm, double &rest) {
					harm = rest = 0;
					for (int k = int(20 / bin); k < int(20000 / bin); ++k) {
						const double h = k * bin / f0, m = std::norm(a[k]);
						if (std::abs(h - std::round(h)) * f0 < 6 * bin)
							harm += m;
						else
							rest += m;
					}
				};
				double f0 = v.probe().vcoHz, best = 0;
				for (double r = 0.98; r <= 1.02; r += 2e-5) {
					double hm, rs;
					split(v.probe().vcoHz * r, hm, rs);
					if (hm > best) {
						best = hm;
						f0 = v.probe().vcoHz * r;
					}
				}
				double harm, rest;
				split(f0, harm, rest);
				if (getenv("TB_ALIASDUMP")) {
					std::vector<std::pair<double, double>> top;
					for (int k = int(20 / bin); k < int(20000 / bin); ++k) {
						const double h = k * bin / f0;
						if (std::abs(h - std::round(h)) * f0 >= 6 * bin)
							top.push_back({std::norm(a[k]), k * bin});
					}
					std::sort(top.rbegin(), top.rend());
					for (int i = 0; i < 6; ++i)
						printf("    %.1f Hz %.1f dB\n", top[i].second, 10 * std::log10(top[i].first / (harm + rest)));
				}
				printf("%s note %d (%.0f Hz): inharmonic %.1f dB\n", sq ? "square" : "saw   ", note, f0, 10 * std::log10(rest / (harm + rest)));
			}
		return 0;
	}
	// time: all scenarios, report % of one core
	double audio = 0, wall = 0;
	for (auto &sc : scenarios()) {
		const auto t0 = std::chrono::steady_clock::now();
		const auto out = render(sc);
		wall += std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
		audio += out.size() / 48000.0;
		printf("  %-12s %5.1f%%\n", sc.name, 100 * std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count() / (out.size() / 48000.0));
	}
	printf("total %.1f%% of one core\n", 100 * wall / audio);
}
