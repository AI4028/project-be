#include <Arduino.h>
#include <BLEDevice.h>
#include <esp_gap_ble_api.h>
#include <freertos/queue.h>

#include "beacon.h"

namespace {

struct GapCompletion {
    esp_gap_ble_cb_event_t event;
    esp_bt_status_t status;
};

QueueHandle_t completions;

void onGapEvent(esp_gap_ble_cb_event_t event, esp_ble_gap_cb_param_t* params) {
    GapCompletion completion{event, ESP_BT_STATUS_SUCCESS};
    switch (event) {
        case ESP_GAP_BLE_ADV_DATA_RAW_SET_COMPLETE_EVT:
            completion.status = params->adv_data_raw_cmpl.status;
            break;
        case ESP_GAP_BLE_ADV_START_COMPLETE_EVT:
            completion.status = params->adv_start_cmpl.status;
            break;
        case ESP_GAP_BLE_ADV_STOP_COMPLETE_EVT:
            completion.status = params->adv_stop_cmpl.status;
            break;
        default:
            return;
    }
    xQueueOverwrite(completions, &completion);
}

bool complete(esp_err_t request, esp_gap_ble_cb_event_t expected) {
    GapCompletion completion{};
    if (request == ESP_OK &&
        xQueueReceive(completions, &completion, pdMS_TO_TICKS(250)) == pdTRUE &&
        completion.event == expected && completion.status == ESP_BT_STATUS_SUCCESS) {
        return true;
    }
    // The controller's state is uncertain. Reset to the idle boot state.
    ESP.restart();
    return false;
}

class EspRadio final : public galjido::Radio {
public:
    bool start(const galjido::Advertisement& data, std::uint32_t receivedAt,
               std::uint32_t lifetimeMs) override {
        auto packet = data;
        if (!complete(esp_ble_gap_config_adv_data_raw(packet.data(), packet.size()),
                      ESP_GAP_BLE_ADV_DATA_RAW_SET_COMPLETE_EVT) ||
            static_cast<std::uint32_t>(millis()) - receivedAt >= lifetimeMs) {
            return false;
        }

        esp_ble_adv_params_t params{};
        params.adv_int_min = 0xA0;  // 100 ms in units of 0.625 ms.
        params.adv_int_max = 0xF0;  // 150 ms.
        params.adv_type = ADV_TYPE_NONCONN_IND;
        params.own_addr_type = BLE_ADDR_TYPE_PUBLIC;
        params.channel_map = ADV_CHNL_ALL;
        params.adv_filter_policy = ADV_FILTER_ALLOW_SCAN_ANY_CON_ANY;
        return complete(esp_ble_gap_start_advertising(&params), ESP_GAP_BLE_ADV_START_COMPLETE_EVT);
    }

    bool stop() override {
        return complete(esp_ble_gap_stop_advertising(), ESP_GAP_BLE_ADV_STOP_COMPLETE_EVT);
    }
};

EspRadio radio;
galjido::Beacon beacon(radio);

}  // namespace

void setupBeacon() {
    Serial.begin(115200);
    completions = xQueueCreate(1, sizeof(GapCompletion));
    if (completions == nullptr || !BLEDevice::init("")) {
        ESP.restart();
        return;
    }
    BLEDevice::setCustomGapHandler(onGapEvent);
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
