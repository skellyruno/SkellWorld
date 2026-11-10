#ifdef NDEBUG
#undef NDEBUG
#endif
#include <SkellCore/Core.h>
#include <SkellCore/backends/SkellyTuneBackend.h>
#include <algorithm>
#include <array>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>
#include <vector>

namespace {
struct MockBackend final : skellcore::PitchFormantBackend {
    int prepareCount=0, resetCount=0;
    void prepare(double, int) override { ++prepareCount; }
    void reset() noexcept override { ++resetCount; }
    int latencySamples() const noexcept override { return 512; }
    void processFrame(const float* in,float* out,int channels) noexcept override {
        for(int c=0;c<channels;++c) out[c]=in[c]*.5f;
    }
};
constexpr double pi=3.1415926535897932384626433832795;
void testLifecycle(){
    skellcore::PitchFormantEngine engine;
    MockBackend a,b;
    float x[2]{.7f,-.5f},y[2]{0,0};
    engine.setBackend(&a);
    assert(engine.hasBackend()&&!engine.isPrepared()&&engine.latencySamples()==0);
    engine.processFrame(x,y,2);
    assert(y[0]==x[0]&&y[1]==x[1]);
    engine.prepare(48000,2);
    assert(engine.isPrepared()&&engine.latencySamples()==512&&a.prepareCount==1);
    engine.processFrame(x,y,2);
    assert(std::abs(y[0]-.35f)<1.e-6f&&y[1]==-.25f);
    engine.reset();assert(a.resetCount==1);
    engine.setBackend(&b);
    assert(!engine.isPrepared()&&engine.latencySamples()==0);
    engine.processFrame(x,y,2);
    assert(y[0]==x[0]&&y[1]==x[1]);
    engine.prepare(96000,1);
    engine.processFrame(x,y,2); // host layout mismatch: safe dry output
    assert(y[0]==x[0]&&y[1]==x[1]);
    engine.setBackend(nullptr);assert(!engine.hasBackend());
    float inA[4]{.1f,.2f,.3f,.4f},inB[4]{-.1f,-.2f,-.3f,-.4f};
    float outA[4]{},outB[4]{};
    const float* in[2]{inA,inB};float* out[2]{outA,outB};
    engine.processBlock(in,out,4,2);
    assert(outA[3]==inA[3]&&outB[0]==inB[0]);
    inA[1]=std::numeric_limits<float>::quiet_NaN();
    engine.processBlock(in,out,4,2);
    assert(outA[1]==0.0f);
    const float* invalid[2]{nullptr,inB};
    engine.processBlock(invalid,out,4,2); // must not dereference nullptr
    engine.processBlock(in,nullptr,4,2);
    engine.processBlock(in,out,0,2);
    engine.processBlock(in,out,4,3);
}
void testUpstreamParity(){
    for (int rate : {44100,48000,96000}) {
        skellcore::backends::SkellyTuneBackend adapter;
        skelly::RealtimeTuner reference;
        skelly::Parameters settings;
        settings.speedMs=0.0f;
        settings.mix=.8f;
        settings.amount=1.f;
        settings.pitchClasses=0x0fff;
        adapter.setParameters(settings); // set before prepare must be retained
        assert(!adapter.isPrepared()&&adapter.latencySamples()==0);
        assert(adapter.outputDelayContract().reportedSamples==0);
        float initialInput[3]{.25f,.5f,-.1f},initialOutput[3]{};
        const float* inp[1]{initialInput};float* outp[1]{initialOutput};
        adapter.processBlock(inp,outp,3,1);
        assert(initialOutput[0]==initialInput[0] && initialOutput[2]==initialInput[2]);
        adapter.prepare(rate,2);
        reference.prepare(rate,2,false,false);
        reference.setParameters(settings);
        assert(adapter.isPrepared() && adapter.latencySamples()==reference.latencySamples());
        constexpr int maxBlock=257;
        std::array<float,maxBlock> left{},right{},producedL{},producedR{},referenceL{},referenceR{};
        const float* source[2]{left.data(),right.data()};
        float* wet[2]{producedL.data(),producedR.data()};
        float* expected[2]{referenceL.data(),referenceR.data()};
        const int pattern[6]{1,64,128,257,17,96};
        int position=0;
        for(int block=0;block<100;++block){
            const int count=pattern[block%6];
            for(int i=0;i<count;++i){
                const double sample=(position+i)/double(rate);
                left[i]=float(.18*std::sin(2*pi*180*sample)+.03*std::sin(2*pi*360*sample));
                right[i]=float(left[i]*.89);
            }
            adapter.processBlock(source,wet,count,2);
            reference.process(source,expected,count,2);
            for(int i=0;i<count;++i){
                assert(std::isfinite(producedL[i])&&std::isfinite(producedR[i]));
                assert(std::abs(producedL[i]-referenceL[i])<=1.e-6f);
                assert(std::abs(producedR[i]-referenceR[i])<=1.e-6f);
            }
            position+=count;
        }
        adapter.reset();
        reference.reset();
        reference.setParameters(settings);
        // A reset retains stored settings in the wrapper.
        const int n=128;
        for(int i=0;i<n;++i){
            left[i]=float(.2*std::sin(2*pi*210*i/rate));
            right[i]=left[i];
        }
        adapter.processBlock(source,wet,n,2);
        reference.process(source,expected,n,2);
        for(int i=0;i<n;++i)assert(std::abs(producedL[i]-referenceL[i])<=1.e-6f);
        std::cout<<"Tuner adapter exact output parity: "<<rate<<" Hz\n";
    }
}
void testMultiInstance(){
    constexpr int instances=6,rate=48000,frames=128;
    std::array<skellcore::backends::SkellyTuneBackend,instances> backends;
    std::array<skellcore::PitchFormantEngine,instances> engines;
    for(int instance=0;instance<instances;++instance){
        engines[instance].setBackend(&backends[instance]);
        engines[instance].prepare(rate,2);
    }
    std::array<float,frames> l{},r{},outputL{},outputR{};
    const float* in[2]{l.data(),r.data()};
    float* out[2]{outputL.data(),outputR.data()};
    for(int block=0;block<48;++block){
        for(int i=0;i<frames;++i){
            const int t=block*frames+i;
            l[i]=float(.16*std::sin(2*pi*196*t/rate));
            r[i]=l[i]*.92f;
        }
        for(int instance=0;instance<instances;++instance){
            engines[instance].processBlock(in,out,frames,2);
            for(int i=0;i<frames;++i)
                assert(std::isfinite(outputL[i])&&std::isfinite(outputR[i]));
        }
    }
}
}
int main(){
    testLifecycle();
    testUpstreamParity();
    testMultiInstance();
    std::cout<<"SkellCore host lifecycle and 6-instance stress tests passed\n";
}
