#ifdef NDEBUG
#undef NDEBUG
#endif
#include <SkellCore/World.h>
#include <cassert>
#include <array>
#include <atomic>
#include <cmath>
#include <iostream>
#include <string>
#include <thread>
using namespace skellcore::world;
int main() {
    Frame hello,parsed;
    assert(make(hello,Kind::Hello,"instance-001","skell.tune","SkellyTune mini"));
    std::array<char,maxLine> buf{};
    std::size_t used=0;
    assert(encode(hello,buf,used) && used<maxLine);
    assert(decode({buf.data(),used},parsed));
    assert(parsed.kind==Kind::Hello && text(parsed.instance)=="instance-001");
    assert(text(parsed.value)=="SkellyTune mini");
    assert(!decode("SW2|HELLO|abc|plugin|name\n",parsed));
    assert(!decode("SW1|EVENT|a|theme|bad|extra\n",parsed));
    assert(!decode("SW1|EVENT|a|theme|bad\ninjection\n",parsed));
    assert(!decode("SW1|EVENT|a|theme|bad\r\n",parsed));
    assert(!decode("SW1|HELLO|a|topic|\n",parsed));
    assert(!make(hello,Kind::Event,"a","key|inject","value"));
    assert(!make(hello,Kind::Event,"a","theme","v\njunk"));
    std::string tooLong(500,'a');
    assert(!make(hello,Kind::Hello,"a","theme",tooLong));
    // Empty queue, overflow and FIFO order.
    Mailbox<4> queue;
    assert(!queue.pop(parsed));
    for(int i=0;i<3;++i){
        assert(make(hello,Kind::Event,"plugin-1","theme",i%2?"ivory":"neon"));
        assert(queue.push(hello));
    }
    assert(!queue.push(hello));
    for(int i=0;i<3;++i) assert(queue.pop(parsed));
    assert(!queue.pop(parsed));
    // Publish 20k frames across two actual threads. Only one producer/consumer.
    Mailbox<64> concurrent;
    std::atomic<unsigned> read{0};
    std::thread producer([&] {
        for(unsigned i=0;i<20000;++i){
            char id[48];
            std::snprintf(id,sizeof id,"p%u",i);
            Frame e;assert(make(e,Kind::Event,id,"meter.peak","0.42"));
            while(!concurrent.push(e))std::this_thread::yield();
        }
    });
    std::thread consumer([&] {
        Frame e;
        for(unsigned i=0;i<20000;++i){
            while(!concurrent.pop(e))std::this_thread::yield();
            char id[48];
            std::snprintf(id,sizeof id,"p%u",i);
            assert(text(e.instance)==id);
            ++read;
        }
    });
    producer.join();consumer.join();
    assert(read==20000);
    std::cout<<"SkellWorld v1 wire, validation and SPSC tests passed\n";
}
