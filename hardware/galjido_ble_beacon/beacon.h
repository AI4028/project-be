#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace galjido {

constexpr std::size_t payloadSize = 14;
using Advertisement = std::array<std::uint8_t, 3 + 2 + payloadSize>;

class Radio {
public:
    virtual bool start(const Advertisement& data, std::uint32_t receivedAt,
                       std::uint32_t lifetimeMs) = 0;
    virtual bool stop() = 0;
    virtual ~Radio() = default;
};

class Beacon {
public:
    explicit Beacon(Radio& radio) : radio_(radio) {}

    void receive(char byte, std::uint32_t now);
    void tick(std::uint32_t now);

private:
    void applyFrame(std::uint32_t now);

    Radio& radio_;
    // Four command bytes, the payload, one space and at most five decimal digits.
    std::array<char, 4 + payloadSize + 1 + 5> line_{};
    std::size_t length_ = 0;
    bool discarding_ = false;
    bool advertising_ = false;
    Advertisement advertisement_{};
    std::uint32_t receivedAt_ = 0;
    std::uint32_t lifetimeMs_ = 0;
};

}  // namespace galjido
