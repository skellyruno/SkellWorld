#pragma once
// Exact SkellyTune real-time DSP imported from skelltune-mini; use its
// declared host PDC, NOT pitch-source age. All allocations occur in prepare().
#include <SkellCore/Core.h>
#include "tune/RealtimeTuner.hpp"

namespace skellcore::backends {
class SkellyTuneBackend final : public PitchFormantBackend {
public:
    // Realtime fixed-dry reference mode only. Experimental PSOLA changes source
    // age; its delay is not safely characterized by this adapter.
    void prepare(double sampleRate, int channels) override {
        prepared_ = false;
        channels_ = std::clamp(channels, 1, 2);
        tuner_.prepare(detail::safeSampleRate(sampleRate), channels_, false, false);
        tuner_.setParameters(parameters_);
        prepared_ = true;
    }
    void reset() noexcept override {
        if (!prepared_) return;
        tuner_.reset();
        tuner_.setParameters(parameters_);
    }
    void setParameters(const skelly::Parameters& parameters) noexcept {
        parameters_ = parameters;
        if (prepared_) tuner_.setParameters(parameters_);
    }
    const skelly::Parameters& parameters() const noexcept { return parameters_; }
    bool isPrepared() const noexcept { return prepared_; }
    int latencySamples() const noexcept override {
        return prepared_ ? tuner_.latencySamples() : 0;
    }
    skelly::DelayContract outputDelayContract() const noexcept {
        return prepared_ ? tuner_.outputDelayContract(false) : skelly::DelayContract{};
    }
    void processFrame(const float* input, float* output, int channels) noexcept override {
        if (!input || !output || channels < 1 || channels > 2) return;
        if (!prepared_ || channels > channels_) {
            for (int c = 0; c < channels; ++c)
                output[c] = static_cast<float>(detail::finite(input[c]));
            return;
        }
        float in[2]{}, out[2]{};
        for (int c = 0; c < channels; ++c) in[c] = input[c];
        const float* src[2] = {in, in + 1};
        float* dst[2] = {out, out + 1};
        tuner_.process(src, dst, 1, channels);
        for (int c = 0; c < channels; ++c) output[c] = out[c];
    }
    void processBlock(const float* const* input, float* const* output,
                      int frames, int channels) noexcept override {
        if (!input || !output || frames <= 0 || channels < 1 || channels > 2) return;
        for (int c = 0; c < channels; ++c)
            if (!input[c] || !output[c]) return;
        if (prepared_ && channels <= channels_) {
            tuner_.process(input, output, frames, channels);
            return;
        }
        for (int c = 0; c < channels; ++c)
            for (int i = 0; i < frames; ++i)
                output[c][i] = static_cast<float>(detail::finite(input[c][i]));
    }
    skelly::PitchEstimate lastPitch() const noexcept { return tuner_.lastPitch(); }
private:
    skelly::RealtimeTuner tuner_;
    skelly::Parameters parameters_ {};
    int channels_ = 2;
    bool prepared_ = false;
};
} // namespace skellcore::backends
