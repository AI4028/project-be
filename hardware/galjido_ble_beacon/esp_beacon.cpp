// Radio layer for the Galjido BLE beacon.
//
// Arduino ESP32 core 3.3.x ships different Bluetooth stacks per chip:
//   - NimBLE:    XIAO ESP32C3 / ESP32S3 / ESP32C6 (Bluedroid is disabled there)
//   - Bluedroid: ESP32 Dev Module
// NimBLE boards call the NimBLE host GAP API directly (ble_gap_adv_*), which avoids
// the Arduino BLEAdvertising wrapper. beacon.cpp (frame parsing, payload, expiry)
// is unchanged. Status lines go to Serial for the Serial Monitor; the bridge
// ignores them.
#include <Arduino.h>
#include <BLEDevice.h>

#include "beacon.h"

#if defined(CONFIG_NIMBLE_ENABLED)
#include <host/ble_gap.h>
#include <host/ble_hs.h>
#elif defined(CONFIG_BLUEDROID_ENABLED)
#include <BLEAdvertising.h>
#else
#error "This board has no BLE stack enabled in the Arduino ESP32 core."
#endif

namespace {

void report(const char* what, const galjido::Advertisement* data, int code) {
    Serial.print(what);
    if (data != nullptr) {
        Serial.print(' ');
        Serial.write(reinterpret_cast<const char*>(data->data()) + 5, galjido::payloadSize);
    }
    if (code != 0) {
        Serial.print(" rc=");
        Serial.print(code);
    }
    Serial.println();
}

#if defined(CONFIG_NIMBLE_ENABLED)

int onGapEvent(struct ble_gap_event*, void*) { return 0; }

class NimbleRadio final : public galjido::Radio {
public:
    bool start(const galjido::Advertisement& data, std::uint32_t receivedAt,
               std::uint32_t lifetimeMs) override {
        int rc = ble_gap_adv_set_data(data.data(), data.size());
        if (rc != 0) {
            report("ADV DATA FAILED", &data, rc);
            return false;
        }
        // Expired while the controller was busy: don't advertise a dead token.
        if (static_cast<std::uint32_t>(millis()) - receivedAt >= lifetimeMs) return false;

        struct ble_gap_adv_params params;
        memset(&params, 0, sizeof(params));
        params.conn_mode = BLE_GAP_CONN_MODE_NON;  // Legacy, non-connectable.
        params.disc_mode = BLE_GAP_DISC_MODE_GEN;
        params.itvl_min = 0xA0;  // 100 ms in units of 0.625 ms.
        params.itvl_max = 0xF0;  // 150 ms.
        rc = ble_gap_adv_start(BLE_OWN_ADDR_PUBLIC, nullptr, BLE_HS_FOREVER, &params,
                               onGapEvent, nullptr);
        report(rc == 0 ? "ADV ON" : "ADV START FAILED", &data, rc);
        return rc == 0;
    }

    bool stop() override {
        const int rc = ble_gap_adv_stop();
        const bool stopped = rc == 0 || rc == BLE_HS_EALREADY;
        report(stopped ? "ADV OFF" : "ADV STOP FAILED", nullptr, stopped ? 0 : rc);
        return stopped;
    }
};

NimbleRadio radio;

#else  // Bluedroid

class BluedroidRadio final : public galjido::Radio {
public:
    bool start(const galjido::Advertisement& data, std::uint32_t receivedAt,
               std::uint32_t lifetimeMs) override {
        BLEAdvertising* advertising = BLEDevice::getAdvertising();
        BLEAdvertisementData packet;
        packet.addData(reinterpret_cast<char*>(const_cast<std::uint8_t*>(data.data())), data.size());
        if (!advertising->setAdvertisementData(packet)) {
            report("ADV DATA FAILED", &data, 0);
            return false;
        }
        if (static_cast<std::uint32_t>(millis()) - receivedAt >= lifetimeMs) return false;
        advertising->setScanResponse(false);
        advertising->setAdvertisementType(ADV_TYPE_NONCONN_IND);
        advertising->setMinInterval(0xA0);
        advertising->setMaxInterval(0xF0);
        const bool started = advertising->start();
        report(started ? "ADV ON" : "ADV START FAILED", &data, 0);
        return started;
    }

    bool stop() override {
        const bool stopped = BLEDevice::getAdvertising()->stop();
        report(stopped ? "ADV OFF" : "ADV STOP FAILED", nullptr, 0);
        return stopped;
    }
};

BluedroidRadio radio;

#endif

galjido::Beacon beacon(radio);

}  // namespace

void setupBeacon() {
    Serial.begin(115200);
    if (!BLEDevice::init("")) {
        ESP.restart();
        return;
    }
#if defined(CONFIG_NIMBLE_ENABLED)
    Serial.println("GALJIDO BEACON READY (NimBLE, direct)");
#else
    Serial.println("GALJIDO BEACON READY (Bluedroid)");
#endif
}

void runBeacon() {
    beacon.tick(millis());
    // Bound each batch so a continuous USB stream cannot starve expiry checks.
    for (unsigned count = 0; count < 64 && Serial.available() > 0; ++count) {
        const int byte = Serial.read();
        if (byte >= 0) beacon.receive(static_cast<char>(byte), millis());
        beacon.tick(millis());
    }
    delay(1);
}
