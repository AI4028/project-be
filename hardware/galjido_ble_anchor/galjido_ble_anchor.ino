// Galjido position anchor: one of the two extra boards for three-board kiosk
// finding. It broadcasts a fixed name forever as soon as it has power (a USB
// charger or power bank is enough; no laptop, no bridge, no internet).
//
//   Name: "LA" + kiosk id + anchor letter, e.g. LAGK01B and LAGK01C.
//
// Flash one board with ANCHOR_LETTER 'B' and the other with 'C'. The kiosk
// board itself keeps running galjido_ble_beacon (it broadcasts LKGK01<code>).
//
// Same radio code as galjido_ble_beacon v3: NimBLE GAP API on XIAO ESP32C3 /
// S3 / C6, Bluedroid on a classic ESP32 Dev Module.
#include <Arduino.h>
#include <BLEDevice.h>

// ---- Change these two lines per board -------------------------------------
#define KIOSK_ID "GK01"
#define ANCHOR_LETTER 'B'  // 'B' for the first extra board, 'C' for the second
// ---------------------------------------------------------------------------

#if defined(CONFIG_NIMBLE_ENABLED)
#include <host/ble_gap.h>
#include <host/ble_hs.h>
#elif defined(CONFIG_BLUEDROID_ENABLED)
#include <BLEAdvertising.h>
#else
#error "This board has no BLE stack enabled in the Arduino ESP32 core."
#endif

namespace {

constexpr char kName[] = {'L', 'A', KIOSK_ID[0], KIOSK_ID[1], KIOSK_ID[2], KIOSK_ID[3],
                          ANCHOR_LETTER};
constexpr size_t kNameLength = sizeof(kName);  // 7
// Flags (LE General Discoverable, BR/EDR not supported) + Complete Local Name.
uint8_t advertisement[3 + 2 + kNameLength] = {0x02, 0x01, 0x06, kNameLength + 1, 0x09};

bool advertising = false;
uint32_t lastAttempt = 0;

void printName() { Serial.write(reinterpret_cast<const uint8_t*>(kName), kNameLength); }

#if defined(CONFIG_NIMBLE_ENABLED)

int onGapEvent(struct ble_gap_event*, void*) { return 0; }

bool startAdvertising() {
    if (!ble_hs_synced()) return false;  // Host still starting up: try again shortly.
    int rc = ble_gap_adv_set_data(advertisement, sizeof(advertisement));
    if (rc != 0) {
        Serial.print("ANCHOR DATA FAILED rc=");
        Serial.println(rc);
        return false;
    }
    struct ble_gap_adv_params params;
    memset(&params, 0, sizeof(params));
    params.conn_mode = BLE_GAP_CONN_MODE_NON;  // Legacy, non-connectable.
    params.disc_mode = BLE_GAP_DISC_MODE_GEN;
    params.itvl_min = 0xA0;  // 100 ms in units of 0.625 ms.
    params.itvl_max = 0xF0;  // 150 ms.
    rc = ble_gap_adv_start(BLE_OWN_ADDR_PUBLIC, nullptr, BLE_HS_FOREVER, &params, onGapEvent,
                           nullptr);
    if (rc != 0 && rc != BLE_HS_EALREADY) {
        Serial.print("ANCHOR START FAILED rc=");
        Serial.println(rc);
        return false;
    }
    return true;
}

bool stillAdvertising() { return ble_gap_adv_active(); }

#else  // Bluedroid

bool startAdvertising() {
    BLEAdvertising* adv = BLEDevice::getAdvertising();
    BLEAdvertisementData packet;
    packet.addData(reinterpret_cast<char*>(advertisement), sizeof(advertisement));
    if (!adv->setAdvertisementData(packet)) return false;
    adv->setScanResponse(false);
    adv->setAdvertisementType(ADV_TYPE_NONCONN_IND);
    adv->setMinInterval(0xA0);
    adv->setMaxInterval(0xF0);
    return adv->start();
}

bool stillAdvertising() { return true; }

#endif

}  // namespace

void setup() {
    Serial.begin(115200);
    memcpy(advertisement + 5, kName, kNameLength);
    if (!BLEDevice::init("")) {
        ESP.restart();
        return;
    }
    Serial.print("GALJIDO ANCHOR READY ");
    printName();
    Serial.println();
}

void loop() {
    const uint32_t now = millis();
    // Start (and restart if the stack ever stops it), checking twice a second.
    if (now - lastAttempt >= 500) {
        lastAttempt = now;
        if (!advertising || !stillAdvertising()) {
            advertising = startAdvertising();
            if (advertising) {
                Serial.print("ANCHOR ON ");
                printName();
                Serial.println();
            }
        }
    }
    delay(10);
}
