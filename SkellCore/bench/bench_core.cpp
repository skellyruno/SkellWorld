#include <SkellCore/Core.h>
#include <SkellCore/backends/SkellyTuneBackend.h>
#include <vector>
#include <memory>
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>

// Informational timings only, NOT a CI timing gate.
int main() {
    using clock=std::chrono::steady_clock;
    constexpr int rate=48000, frames=rate*4, patternSize=4096;
    std::array<std::array<float,2>,patternSize> input{};
    for(int i=0;i<patternSize;++i){
        input[i][0]=.8f*float(std::sin(i*.131));
        input[i][1]=.6f*float(std::cos(i*.089));
    }
    volatile double finalChecksum=0;
    for(auto quality : {skellcore::TruePeakLimiter::Quality::Economy,
                        skellcore::TruePeakLimiter::Quality::Standard}) {
        skellcore::TruePeakLimiter limiter;limiter.prepare(rate,2,quality);
        std::array<float,2> out{};
        for(int i=0;i<patternSize;++i)limiter.processFrame(input[i].data(),out.data(),2);
        double checksum=0;
        const auto start=clock::now();
        for(int i=0;i<frames;++i){
            limiter.processFrame(input[i&(patternSize-1)].data(),out.data(),2);
            checksum+=out[0];
        }
        const double elapsed=std::chrono::duration<double>(clock::now()-start).count();
        finalChecksum=checksum;
        std::cout<<(quality==skellcore::TruePeakLimiter::Quality::Economy?"Economy":"Standard")
                 <<" limiter: "<<std::fixed<<std::setprecision(3)
                 <<elapsed/4.0*100.0<<"% of one 48k real-time stream (wall time), "
                 <<elapsed/frames*1.e9<<" ns/stereo frame\n";
    }
    skellcore::FDNReverb reverb;reverb.prepare(rate);
    double checksum=0;
    const auto start=clock::now();
    for(int i=0;i<frames;++i) {
        const auto out=reverb.processFrame(input[i&(patternSize-1)][0],0.f);
        checksum+=out[0];
    }
    const double elapsed=std::chrono::duration<double>(clock::now()-start).count();
    finalChecksum=checksum;
    std::cout<<"FDN reverb: "<<elapsed/4.0*100.0
             <<"% of one 48k real-time stream (wall time)\n";
    // The pitch engine is likely a larger CPU cost than an FDN. Benchmark
    // its true block-processing adapter on continuous voiced audio.
    std::vector<float> vocalL(frames), vocalR(frames);
    for(int i=0;i<frames;++i) {
        vocalL[i]=.22f*float(std::sin(2*3.141592653589793*220.0*i/rate));
        vocalR[i]=vocalL[i]*.92f;
    }
    skellcore::backends::SkellyTuneBackend tuning;
    tuning.prepare(rate,2);
    constexpr int block=256;
    std::array<float,block> outL{},outR{};
    double pitchChecksum=0;
    auto pitchStart=clock::now();
    for(int pos=0;pos<frames;pos+=block){
        const int count=std::min(block,frames-pos);
        const float* inPtrs[2]{vocalL.data()+pos,vocalR.data()+pos};
        float* outPtrs[2]{outL.data(),outR.data()};
        tuning.processBlock(inPtrs,outPtrs,count,2);
        pitchChecksum+=outL[0];
    }
    const double pitchElapsed=std::chrono::duration<double>(clock::now()-pitchStart).count();
    finalChecksum=pitchChecksum;
    std::cout<<"SkellyTune realtime block backend: "
             <<pitchElapsed/4.0*100.0
             <<"% of one 48k real-time stream (wall time)\n";

    // Multi-instance budget diagnostic. Each engine is independently prepared
    // *before* the timer. Instances are processed serially to model one
    // saturated DAW worker thread (not a substitute for real FL Studio).
    for (const int instanceCount : {1,4,8}) {
        std::vector<std::unique_ptr<skellcore::backends::SkellyTuneBackend>> engines;
        engines.reserve(static_cast<std::size_t>(instanceCount));
        for (int i=0;i<instanceCount;++i) {
            auto engine=std::make_unique<skellcore::backends::SkellyTuneBackend>();
            engine->prepare(rate,2);
            engines.push_back(std::move(engine));
        }
        double sum=0;
        const auto started=clock::now();
        for (int pos=0;pos<frames;pos+=block) {
            const int count=std::min(block,frames-pos);
            const float* src[2]{vocalL.data()+pos,vocalR.data()+pos};
            float* dst[2]{outL.data(),outR.data()};
            for (auto& engine : engines) {
                engine->processBlock(src,dst,count,2);
                sum+=outL[0];
            }
        }
        const double seconds=std::chrono::duration<double>(clock::now()-started).count();
        finalChecksum=sum;
        std::cout<<"SkellyTune "<<instanceCount
                 <<" simultaneous instances (serial, 256-sample blocks): "
                 <<seconds/4.0*100.0
                 <<"% of 48k stereo real-time budget (wall time)\n";
    }
    if(finalChecksum==1.e100)std::cerr<<"unreachable\n";
}
