/* Model-303: the Lemus TB-303 voice (src/lemus, with the Devil Fish mods) as mpc-vst-plugins' mpc_engine()
 * (wrapper/engine.h): 44.1 kHz, interleaved int16 stereo, 128-frame blocks.
 *
 * Parameters are kept in their own units (knobs 0-10, TUNE in cents, options by index) and turned into the voice's
 * pot rotations on every change. MIDI follows the TB-303's own software, the TB-03 and the TD-3 (and Open303):
 * velocity 100 or more is an accent, a note that starts while another is held slides to it without a new gate,
 * and releasing the newest of several held notes slides back to the one before. CC65 (portamento, as the Acid
 * sequencer sends with its slides) also makes a note that starts while the gate is still up slide. */
#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <strings.h>
#include <new>

extern "C" {
#include "engine.h"
#include "params.h"
}
#include "voice.h"

namespace {

constexpr int kHostRate = 44100;
constexpr int kMaxHeld = 16;

int keyIndex(const char *k)
{
	for (int i = 0; i < NPARAMS; ++i)
		if (!strcmp(PARAMS[i].key, k))
			return i;
	return -1;
}

struct Inst {
	// Both qualities are prepared at creation and QUALITY only picks which one renders: re-preparing a voice
	// renders its 0.6 s of warm-up, far too long for a switch (or a Q-Link sweep) on the audio thread's lock.
	tb303::Voice voices[2];     // [0] HQ (Lemus's 4x), [1] ECO (2x, the prewarped ladder)
	tb303::Voice *voice = &voices[1];
	float vals[NPARAMS];

	// The voice sleeps (renders zeros) once its gate has been off and it has been silent for kSleepBlocks: it is a
	// full circuit simulation even when idle. A note, or any control change, wakes it.
	static constexpr float kSilence = 1e-6f;                // -120 dB
	static constexpr int kSleepBlocks = 44100 / 128 / 2;    // 0.5 s: past the longest tail
	bool asleep = false;
	int quietBlocks = 0;

	// MIDI to the CPU lines (tb303::MidiDriver's rules, fixed storage: nothing allocates on the audio thread)
	tb303::CpuLines lines;
	int held[kMaxHeld];
	int nHeld = 0;
	unsigned triggers = 0;
	bool portamento = false; // CC65

	float mono[128];

	Inst()
	{
		voices[0].setMinInternalRate(176000);
		voices[1].setMinInternalRate(88000);
		for (auto &v : voices)
			v.prepare(kHostRate);
		for (int i = 0; i < NPARAMS; ++i) {
			const param_t &p = PARAMS[i];
			vals[i] = p.nopts ? std::round(p.def * (p.nopts - 1)) : p.min + p.def * (p.max - p.min);
		}
		apply();
	}

	float val(const char *k) const { return vals[keyIndex(k)]; }
	int opt(const char *k) const { return int(val(k)); }

	void apply()
	{
		// AUTO: the 2x VCF/VCA on the armhf (Gen1) devices, Lemus's 4x on aarch64 (Gen2)
		const int q = opt("quality"); // HQ, AUTO, ECO (top to bottom on the panel's switch)
#if defined(__aarch64__)
		const bool hq = q != 2;       // AUTO: Lemus's 4x on the faster Gen2 devices
#else
		const bool hq = q == 0;       // AUTO: the 2x on Gen1 (docs: a third of a core)
#endif
		voice = &voices[hq ? 0 : 1];
		tb303::Controls c;
		c.tuning = 0.5 + val("tune") / 1400.0; // the knob spans +/-700 cents (service notes)
		c.cutoff = val("cutoff") / 10;
		c.resonance = val("resonance") / 10;
		c.envMod = val("env_mod") / 10;
		c.decay = val("decay") / 10;
		c.accent = val("accent") / 10;
		c.volume = val("volume") / 10;
		c.square = opt("waveform") == 1;
		c.devilFish = opt("devil_fish") == 1;
		c.softAttack = val("soft_attack") / 10;
		c.normalDecay = val("normal_decay") / 10;
		c.accentDecay = val("accent_decay") / 10;
		c.filterTracking = val("filter_tracking") / 10;
		c.overdrive = val("overdrive") / 10;
		c.slideTime = val("slide_time") / 10;
		c.filterFM = val("filter_fm") / 10;
		c.sweepSpeed = opt("sweep_speed");
		// the three-way switches' options run top to bottom as on the panel: 2, 1, 0 and HIGH, MID, LOW
		c.accentSweep = 2 - opt("accent_sweep");
		c.muffler = 2 - opt("muffler");
		c.subOsc = opt("sub_osc") == 1 ? 3 - opt("sub_level") : 0;
		c.waveOff = opt("vco") == 1;
		for (auto &v : voices)
			v.setControls(c);
		sendLines();
	}

	void sendLines()
	{
		tb303::CpuLines l = lines;
		l.accent = l.accent || opt("accent_hold") == 1;
		for (auto &v : voices)
			v.setLines(l, triggers);
		asleep = false;
		quietBlocks = 0;
	}

	void noteOn(int note, int vel)
	{
		const bool legato = nHeld > 0 || (portamento && lines.gate);
		nHeld = int(std::remove(held, held + nHeld, note) - held);
		if (nHeld == kMaxHeld) {
			std::copy(held + 1, held + nHeld, held);
			--nHeld;
		}
		held[nHeld++] = note;
		lines.note = note;
		lines.accent = vel >= 100;
		lines.slide = legato;
		lines.gate = true;
		if (!legato)
			++triggers;
	}

	void noteOff(int note)
	{
		const bool wasCurrent = nHeld > 0 && held[nHeld - 1] == note;
		int *end = std::remove(held, held + nHeld, note);
		nHeld = int(end - held);
		if (nHeld == 0) {
			lines.gate = false;
		} else if (wasCurrent) {
			lines.note = held[nHeld - 1];
			lines.slide = true;
		}
	}

	void allNotesOff()
	{
		nHeld = 0;
		lines.gate = false;
	}

	// "key=value;..." of every parameter, in its own units (options by name)
	int saveState(char *buf, int len) const
	{
		int n = 0;
		for (int i = 0; i < NPARAMS && n < len; ++i) {
			const param_t &p = PARAMS[i];
			if (p.nopts)
				n += snprintf(buf + n, size_t(len - n), "%s=%s;", p.key, p.opts[int(vals[i])]);
			else
				n += snprintf(buf + n, size_t(len - n), "%s=%g;", p.key, double(vals[i]));
		}
		return n < len ? n : -1;
	}

	void setValue(int i, const char *v)
	{
		const param_t &p = PARAMS[i];
		if (p.nopts) {
			int idx = -1;
			if (isdigit((unsigned char)v[0]))
				idx = atoi(v);
			else
				for (int o = 0; o < p.nopts; ++o)
					if (!strcasecmp(v, p.opts[o]))
						idx = o;
			if (idx >= 0 && idx < p.nopts)
				vals[i] = float(idx);
		} else {
			vals[i] = std::clamp(float(atof(v)), p.min, p.max);
		}
	}

	void loadState(const char *s)
	{
		char key[64], value[64];
		while (*s) {
			const char *eq = strchr(s, '='), *semi = strchr(s, ';');
			if (!eq || !semi || eq > semi)
				break;
			const size_t kl = std::min(size_t(eq - s), sizeof key - 1), vl = std::min(size_t(semi - eq - 1), sizeof value - 1);
			memcpy(key, s, kl);
			key[kl] = 0;
			memcpy(value, eq + 1, vl);
			value[vl] = 0;
			const int i = keyIndex(key);
			if (i >= 0)
				setValue(i, value);
			s = semi + 1;
		}
		apply();
	}
};

void *create(const char *)
{
	return new (std::nothrow) Inst();
}

void destroy(void *e)
{
	delete static_cast<Inst *>(e);
}

void midi(void *e, const uint8_t *m, int len)
{
	Inst &t = *static_cast<Inst *>(e);
	if (len < 2)
		return;
	const int st = m[0] & 0xf0;
	if (st == 0x90 && len >= 3)
		m[2] ? t.noteOn(m[1], m[2]) : t.noteOff(m[1]);
	else if (st == 0x80 && len >= 3)
		t.noteOff(m[1]);
	else if (st == 0xb0 && len >= 3) {
		if (m[1] == 65)
			t.portamento = m[2] >= 64;
		else if (m[1] == 120 || m[1] == 123)
			t.allNotesOff();
	} else
		return;
	t.sendLines();
}

void setParam(void *e, const char *k, const char *v)
{
	Inst &t = *static_cast<Inst *>(e);
	if (!strcmp(k, "state")) {
		t.loadState(v);
		return;
	}
	const int i = keyIndex(k);
	if (i < 0)
		return;
	t.setValue(i, v);
	t.apply();
}

int getParam(void *e, const char *k, char *buf, int len)
{
	const Inst &t = *static_cast<const Inst *>(e);
	if (!strcmp(k, "state"))
		return t.saveState(buf, len);
	const int i = keyIndex(k);
	if (i < 0)
		return 0;
	const param_t &p = PARAMS[i];
	const int n = p.nopts ? snprintf(buf, size_t(len), "%s", p.opts[int(t.vals[i])]) : snprintf(buf, size_t(len), "%g", double(t.vals[i]));
	return n > 0 && n < len ? n : 0;
}

void render(void *e, int16_t *out, int frames)
{
	Inst &t = *static_cast<Inst *>(e);
	frames = std::min(frames, 128);
#if defined(__aarch64__)
	// Flush denormals to zero for this block (FPCR.FZ), restoring the host's setting after: armv7 NEON always does,
	// aarch64 does not, and denormal arithmetic is far slower there
	struct Ftz {
		uint64_t saved;
		Ftz() { asm volatile("mrs %0, fpcr" : "=r"(saved)); asm volatile("msr fpcr, %0" : : "r"(saved | (1ull << 24))); }
		~Ftz() { asm volatile("msr fpcr, %0" : : "r"(saved)); }
	} ftz;
#endif
	if (t.asleep) {
		memset(out, 0, sizeof(int16_t) * 2 * size_t(frames));
		return;
	}
	t.voice->render(t.mono, frames);
	float peak = 0;
	for (int i = 0; i < frames; ++i)
		peak = std::max(peak, std::fabs(t.mono[i]));
	t.quietBlocks = (peak < Inst::kSilence && !t.lines.gate) ? t.quietBlocks + 1 : 0;
	t.asleep = t.quietBlocks >= Inst::kSleepBlocks;
	for (int i = 0; i < frames; ++i) {
		const float s = std::clamp(t.mono[i], -1.0f, 1.0f) * 32767.0f;
		out[2 * i] = out[2 * i + 1] = int16_t(std::lrint(s));
	}
}

const mpc_engine_t api = {create, destroy, midi, setParam, getParam, render, nullptr, nullptr};

} // namespace

extern "C" const mpc_engine_t *mpc_engine(void)
{
	return &api;
}
