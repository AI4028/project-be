#include "beacon.h"

#include <cassert>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

namespace {

using galjido::Advertisement;
using galjido::Beacon;

const std::string first = "LKGK017H3KQ9ZC";
const std::string second = "LKGK01ABCDEFGH";

struct FakeRadio : galjido::Radio {
    std::vector<std::string> events;
    bool startSucceeds = true;
    bool stopSucceeds = true;

    bool start(const Advertisement& data, std::uint32_t, std::uint32_t) override {
        const Advertisement::value_type expectedHeader[] = {2, 0x01, 0x06, 15, 0x09};
        for (std::size_t i = 0; i < sizeof(expectedHeader); ++i) {
            assert(data[i] == expectedHeader[i]);
        }
        assert(data.size() == 19);
        events.emplace_back(data.begin() + 5, data.end());
        return startSucceeds;
    }

    bool stop() override {
        events.emplace_back("stop");
        return stopSucceeds;
    }
};

void send(Beacon& beacon, const std::string& bytes, std::uint32_t at) {
    for (const char byte : bytes) beacon.receive(byte, at);
}

void updatesAndExpiry() {
    FakeRadio radio;
    Beacon beacon(radio);
    beacon.tick(0);
    send(beacon, "ADV " + first, 100);
    beacon.tick(200);
    assert(radio.events.empty());
    send(beacon, " 59000\n", 300);
    send(beacon, "ADV " + second + " 59000\n", 30300);
    beacon.tick(59300);  // The old deadline must no longer stop the radio.
    beacon.tick(89299);
    assert((radio.events == std::vector<std::string>{first, "stop", second}));
    beacon.tick(89300);
    beacon.tick(89301);
    assert((radio.events == std::vector<std::string>{first, "stop", second, "stop"}));
    send(beacon, "ADV " + first + " 1\n", 89302);
    beacon.tick(89303);
    assert((radio.events == std::vector<std::string>{first, "stop", second, "stop", first, "stop"}));
}

void repeatedTokenKeepsRadioRunningAcrossClockRollover() {
    FakeRadio radio;
    Beacon beacon(radio);
    const auto start = std::numeric_limits<std::uint32_t>::max() - 10;
    send(beacon, "ADV " + first + " 30\n", start);
    send(beacon, "ADV " + first + " 20\n", 4);
    beacon.tick(19);
    beacon.tick(23);
    assert((radio.events == std::vector<std::string>{first}));
    beacon.tick(24);
    assert((radio.events == std::vector<std::string>{first, "stop"}));
}

void malformedInputPreservesDeadlineAndResynchronizes() {
    FakeRadio radio;
    Beacon beacon(radio);
    send(beacon, "ADV " + first + " 100\n", 0);
    const std::vector<std::string> malformed{
        "\n", "STOP\n", "adv " + second + " 90\n", "ADV XXGK01ABCDEFGH 90\n",
        "ADV LKG-01ABCDEFGH 90\n", "ADV LKGK01ABCDUFGH 90\n",
        "ADV " + second + "\n", "ADV " + second + " 0\n", "ADV " + second + " 60001\n",
        "ADV " + second + " -90\n", "ADV " + second + " +90\n", "ADV " + second + " 90x\n",
        "ADV " + second + " 90 \n", "ADV " + second + " 90\r\n",
        "ADV LKGK01ABC" + std::string(1, '\0') + "EFGH 90\n",
        std::string(128, 'X') + "ADV " + second + " 90\n",
    };
    for (const auto& frame : malformed) send(beacon, frame, 75);
    beacon.tick(99);
    assert((radio.events == std::vector<std::string>{first}));
    beacon.tick(100);
    send(beacon, "ADV " + second + " 60000\n", 101);
    assert((radio.events == std::vector<std::string>{first, "stop", second}));
}

void failedRadioOperationsDoNotExtendExpiry() {
    FakeRadio radio;
    Beacon beacon(radio);
    send(beacon, "ADV " + first + " 100\n", 0);
    radio.stopSucceeds = false;
    send(beacon, "ADV " + second + " 100\n", 50);
    assert((radio.events == std::vector<std::string>{first, "stop"}));
    radio.stopSucceeds = true;
    beacon.tick(100);
    assert((radio.events == std::vector<std::string>{first, "stop", "stop"}));
    radio.startSucceeds = false;
    send(beacon, "ADV " + second + " 100\n", 101);
    beacon.tick(201);
    assert((radio.events == std::vector<std::string>{first, "stop", "stop", second}));
}

}  // namespace

int main() {
    updatesAndExpiry();
    repeatedTokenKeepsRadioRunningAcrossClockRollover();
    malformedInputPreservesDeadlineAndResynchronizes();
    failedRadioOperationsDoNotExtendExpiry();
    std::cout << "ESP32 beacon firmware: 4 host test cases passed\n";
}
