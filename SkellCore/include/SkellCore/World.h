#pragma once
// SkellWorld v1: safe, transport-agnostic identity and presence/event protocol.
// No networking, allocation, mutex or DSP changes in this header.
#include <array>
#include <atomic>
#include <algorithm>
#include <cstddef>
#include <cstdio>
#include <cstring>
#include <string_view>
#include <type_traits>

namespace skellcore::world {
constexpr unsigned protocolVersion = 1;
constexpr std::size_t maxLine = 256;
constexpr int defaultPort = 48673;
enum class Kind { Hello, Welcome, Peer, Event, Bye, Error, Invalid };

struct Frame {
    Kind kind = Kind::Invalid;
    std::array<char, 48> instance{};
    std::array<char, 48> topic{};
    std::array<char, 96> value{};
};

inline constexpr const char* keyword(Kind k) noexcept {
    switch (k) {
        case Kind::Hello: return "HELLO";
        case Kind::Welcome: return "WELCOME";
        case Kind::Peer: return "PEER";
        case Kind::Event: return "EVENT";
        case Kind::Bye: return "BYE";
        case Kind::Error: return "ERROR";
        default: return "INVALID";
    }
}
inline Kind kindFromString(std::string_view s) noexcept {
    for (auto k : {Kind::Hello, Kind::Welcome, Kind::Peer, Kind::Event, Kind::Bye, Kind::Error})
        if (s == keyword(k)) return k;
    return Kind::Invalid;
}
// Identifiers are stable ASCII-only IDs. Values are short printable text.
// Reject control chars, pipe separators and embedded NUL.
inline bool valid(std::string_view s, bool value = false) noexcept {
    if (s.empty()) return false;
    for (unsigned char c : s) {
        if (c < (value ? 32 : 33) || c > 126 || c == '|' || c == '\\') return false;
        if (!value && !(c >= 'a' && c <= 'z') && !(c >= 'A' && c <= 'Z') &&
            !(c >= '0' && c <= '9') && c != '-' && c != '_' && c != '.') return false;
    }
    return true;
}
template<std::size_t N>
inline bool copyField(std::array<char,N>& to, std::string_view from, bool value = false) noexcept {
    if (from.size() >= N || !valid(from,value)) return false;
    to.fill(0);
    std::memcpy(to.data(), from.data(), from.size());
    return true;
}
inline bool make(Frame& out, Kind kind, std::string_view instance,
                 std::string_view topic, std::string_view value) noexcept {
    if (kind == Kind::Invalid) return false;
    Frame result;
    result.kind = kind;
    if (!copyField(result.instance, instance) || !copyField(result.topic, topic) ||
        !copyField(result.value, value, true)) return false;
    out = result;
    return true;
}
template<std::size_t N>
inline std::string_view text(const std::array<char,N>& s) noexcept {
    const auto terminator = std::find(s.begin(), s.end(), '\0');
    if (terminator == s.end()) return {};
    return {s.data(), static_cast<std::size_t>(terminator - s.begin())};
}
// Only invoke on the UI/background side; encoding is NEVER an audio-thread API.
inline bool encode(const Frame& f, std::array<char,maxLine>& target, std::size_t& length) noexcept {
    length = 0;
    if (f.kind == Kind::Invalid || !valid(text(f.instance)) ||
        !valid(text(f.topic)) || !valid(text(f.value),true)) return false;
    const int written = std::snprintf(target.data(),target.size(),"SW1|%s|%s|%s|%s\n",
                                     keyword(f.kind),f.instance.data(),f.topic.data(),f.value.data());
    if (written <= 0 || static_cast<std::size_t>(written) >= target.size()) return false;
    length = static_cast<std::size_t>(written);
    return true;
}
inline bool decode(std::string_view src, Frame& out) noexcept {
    if (src.empty() || src.size() >= maxLine) return false;
    if (src.back() == '\n') src.remove_suffix(1);
    if (src.empty() || src.back() == '\r' || src.find('\n') != src.npos ||
        src.find('\0') != src.npos) return false;
    std::array<std::string_view,5> parts;
    std::size_t start = 0;
    for (std::size_t i=0;i<parts.size();++i) {
        const auto at = src.find('|',start);
        if (i==parts.size()-1) {
            if (at!=src.npos) return false;
            parts[i]=src.substr(start);
        } else {
            if (at==src.npos) return false;
            parts[i]=src.substr(start,at-start);
            start=at+1;
        }
    }
    if (parts[0]!="SW1") return false;
    return make(out,kindFromString(parts[1]),parts[2],parts[3],parts[4]);
}
// One producer / one consumer, fixed capacity; no allocation or blocking.
// Can carry meter/transport telemetry from AUDIO -> BACKGROUND, but must never
// be used from two audio producer threads or two consumer threads.
template<std::size_t Capacity>
class Mailbox {
    static_assert(Capacity>=2,"Mailbox needs at least two slots");
public:
    bool push(const Frame& frame) noexcept {
        const std::size_t write=write_.load(std::memory_order_relaxed);
        const auto next=(write+1)%Capacity;
        if (next==read_.load(std::memory_order_acquire)) return false;
        slots_[write]=frame;
        write_.store(next,std::memory_order_release);
        return true;
    }
    bool pop(Frame& frame) noexcept {
        const auto read=read_.load(std::memory_order_relaxed);
        if (read==write_.load(std::memory_order_acquire)) return false;
        frame=slots_[read];
        read_.store((read+1)%Capacity,std::memory_order_release);
        return true;
    }
    void resetWhenStopped() noexcept {
        read_.store(0,std::memory_order_relaxed);
        write_.store(0,std::memory_order_relaxed);
    }
private:
    std::array<Frame,Capacity> slots_{};
    std::atomic<std::size_t> read_{0}, write_{0};
};
static_assert(std::is_trivially_copyable_v<Frame>,"Frames must remain cheap and allocation free");
} // namespace skellcore::world
