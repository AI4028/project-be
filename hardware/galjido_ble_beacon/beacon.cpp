#include "beacon.h"

#include <algorithm>
#include <cstring>

namespace galjido {
namespace {

constexpr std::uint32_t maxLifetimeMs = 60000;
constexpr char tokenAlphabet[] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";

bool validKioskCharacter(char value) {
    return (value >= 'A' && value <= 'Z') || (value >= '0' && value <= '9');
}

bool validTokenCharacter(char value) {
    return value != '\0' && std::strchr(tokenAlphabet, value) != nullptr;
}

}  // namespace

void Beacon::receive(char byte, std::uint32_t now) {
    if (byte == '\n') {
        if (!discarding_) applyFrame(now);
        length_ = 0;
        discarding_ = false;
    } else if (length_ == line_.size()) {
        discarding_ = true;
    } else {
        line_[length_++] = byte;
    }
}

void Beacon::tick(std::uint32_t now) {
    // Unsigned subtraction also handles the millis() rollover.
    if (advertising_ && now - receivedAt_ >= lifetimeMs_ && radio_.stop()) {
        advertising_ = false;
    }
}

void Beacon::applyFrame(std::uint32_t now) {
    const char* payload = line_.data() + 4;
    constexpr auto lifetimeOffset = 4 + payloadSize + 1;
    if (length_ <= lifetimeOffset || std::memcmp(line_.data(), "ADV LK", 6) != 0 ||
        payload[payloadSize] != ' ' ||
        !std::all_of(payload + 2, payload + 6, validKioskCharacter) ||
        !std::all_of(payload + 6, payload + payloadSize, validTokenCharacter)) {
        return;
    }

    std::uint32_t lifetime = 0;
    for (std::size_t index = lifetimeOffset; index < length_; ++index) {
        const char digit = line_[index];
        if (digit < '0' || digit > '9') return;
        lifetime = lifetime * 10 + (digit - '0');
    }
    if (lifetime == 0 || lifetime > maxLifetimeMs) return;

    // Flags (general discoverable, BLE-only) followed by Complete Local Name.
    Advertisement data{2, 0x01, 0x06, payloadSize + 1, 0x09};
    std::copy_n(payload, payloadSize, data.begin() + 5);

    if (advertising_ && (now - receivedAt_ >= lifetimeMs_ || data != advertisement_)) {
        if (!radio_.stop()) return;
        advertising_ = false;
    }
    if (!advertising_) {
        advertising_ = radio_.start(data, now, lifetime);
        if (!advertising_) return;
        advertisement_ = data;
    }
    receivedAt_ = now;
    lifetimeMs_ = lifetime;
}

}  // namespace galjido
