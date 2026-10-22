#pragma once

#include <vector>

namespace tb303 {

// Decimates by 2^stages with a chain of half-band FIR filters (Kaiser-windowed sinc). The
// voice runs at the oversampled rate and only needs the way down.
class Decimator {
public:
	// stages 0-3 (factor 1, 2, 4 or 8). The last stage sets the pass band's edge and gets the
	// long filter; the earlier ones only keep their images out of it. Half lengths are in odd
	// taps per side and must be multiples of 4.
	void setStages(int stages, int lastHalfLength = 32, int firstHalfLength = 12);
	int factor() const { return 1 << m_stages; }
	void reset();

	// Consumes factor() input samples, returns one output sample.
	float process(const float *in);

	// Delay at the output rate, in output samples.
	double latency() const;

private:
	struct HalfBand {
		std::vector<double> taps; // odd-indexed taps of the half-band filter (the even ones are 0 except the centre)
		// Polyphase: the odd taps only ever meet the first sample of each input pair, so those
		// are kept apart (doubled for wrap-free reads) and weighted by `weights`, the symmetric
		// odd taps written out in full; the second samples only feed the centre tap.
		// Float: the inputs are float already, and float rounding (~-140 dB) is far under the
		// filters' stop bands; on ARM it lets NEON take four taps at a time.
		std::vector<float> weights; // 2n
		std::vector<float> even;    // 2 * 2n first-of-pair samples
		std::vector<float> odd;     // 2 * 2n second-of-pair samples
		int pos = 0;
		int len = 0; // 2n
		void design(int halfLength, double transition, double attenuationDb);
		void reset();
		float process(float a, float b); // two input samples in, one out
	};
	int m_stages = 0;
	std::vector<HalfBand> m_bands;
	std::vector<float> m_work;
};

} // namespace tb303
