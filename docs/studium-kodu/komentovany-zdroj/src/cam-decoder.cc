// Pomocný dekóder CAM cez pripnutú knižnicu Vanetza. Používa sa pri čítaní potvrdených polí z
// reálnych bajtov paketu; nezúčastňuje sa vysielania.
#include <vanetza/asn1/cam.hpp>
#include <iostream>
#include <iomanip>
#include <string>
#include <vector>

// Vstupom je hexadecimálny reťazec raw CAM. Program ho prevedie na bajty, nechá Vanetza dekódovať
// a validovať ASN.1 a vypíše potvrdené významové polia do JSON. Chybový návrat znamená, že bajty
// nie sú platný CAM podľa pripnutej schémy.
int main(int argc, char** argv) {
    if (argc != 2) return 2;
    const std::string hex = argv[1];
    if (hex.size() % 2 || hex.size() > 8192) return 2;
    std::vector<unsigned char> bytes;
    for (std::size_t i = 0; i < hex.size(); i += 2) {
        try {
            std::size_t used = 0;
            const auto value = std::stoul(hex.substr(i, 2), &used, 16);
            if (used != 2 || value > 255) return 2;
            bytes.push_back(static_cast<unsigned char>(value));
        } catch (...) { return 2; }
    }
    vanetza::asn1::r2::Cam cam;
    if (!cam.decode(bytes.begin(), bytes.end()) || !cam.validate()) return 1;
    const auto& h = cam->header;
    const auto& p = cam->cam.camParameters;
    const auto& pos = p.basicContainer.referencePosition;
    std::cout << std::setprecision(10);
    std::cout << "{\"protocol_version\":" << h.protocolVersion
              << ",\"message_id\":" << h.messageId
              << ",\"station_id\":" << h.stationId
              << ",\"generation_delta_time_ms\":" << cam->cam.generationDeltaTime
              << ",\"station_type\":" << p.basicContainer.stationType
              << ",\"latitude_deg\":" << pos.latitude / 10000000.0
              << ",\"latitude_code\":" << pos.latitude
              << ",\"longitude_deg\":" << pos.longitude / 10000000.0
              << ",\"longitude_code\":" << pos.longitude
              << ",\"altitude_m\":" << pos.altitude.altitudeValue / 100.0
              << ",\"altitude_code\":" << pos.altitude.altitudeValue
              << ",\"position_confidence_major_m\":" << pos.positionConfidenceEllipse.semiMajorAxisLength / 100.0
              << ",\"position_confidence_major_code\":" << pos.positionConfidenceEllipse.semiMajorAxisLength
              << ",\"position_confidence_minor_m\":" << pos.positionConfidenceEllipse.semiMinorAxisLength / 100.0
              << ",\"position_confidence_minor_code\":" << pos.positionConfidenceEllipse.semiMinorAxisLength
              << ",\"position_confidence_orientation_code\":" << pos.positionConfidenceEllipse.semiMajorAxisOrientation
              << ",\"altitude_confidence_code\":" << pos.altitude.altitudeConfidence
              << ",\"high_frequency_type\":" << p.highFrequencyContainer.present
              << ",\"low_frequency_present\":" << (p.lowFrequencyContainer ? "true" : "false");
    if (p.highFrequencyContainer.present == Vanetza_ITS2_HighFrequencyContainer_PR_basicVehicleContainerHighFrequency) {
        const auto& q = p.highFrequencyContainer.choice.basicVehicleContainerHighFrequency;
        std::cout << ",\"heading_deg\":" << q.heading.headingValue / 10.0
                  << ",\"heading_code\":" << q.heading.headingValue
                  << ",\"heading_confidence_code\":" << q.heading.headingConfidence
                  << ",\"speed_mps\":" << q.speed.speedValue / 100.0
                  << ",\"speed_code\":" << q.speed.speedValue
                  << ",\"speed_confidence_code\":" << q.speed.speedConfidence
                  << ",\"drive_direction\":" << q.driveDirection
                  << ",\"vehicle_length_m\":" << q.vehicleLength.vehicleLengthValue / 10.0
                  << ",\"vehicle_length_code\":" << q.vehicleLength.vehicleLengthValue
                  << ",\"vehicle_length_confidence_code\":" << q.vehicleLength.vehicleLengthConfidenceIndication
                  << ",\"vehicle_width_m\":" << q.vehicleWidth / 10.0
                  << ",\"vehicle_width_code\":" << q.vehicleWidth
                  << ",\"longitudinal_acceleration_mps2\":" << q.longitudinalAcceleration.value / 10.0
                  << ",\"longitudinal_acceleration_code\":" << q.longitudinalAcceleration.value
                  << ",\"longitudinal_acceleration_confidence_code\":" << q.longitudinalAcceleration.confidence
                  << ",\"curvature_code\":" << q.curvature.curvatureValue
                  << ",\"curvature_confidence_code\":" << q.curvature.curvatureConfidence
                  << ",\"curvature_calculation_mode\":" << q.curvatureCalculationMode
                  << ",\"yaw_rate_degps\":" << q.yawRate.yawRateValue / 100.0
                  << ",\"yaw_rate_code\":" << q.yawRate.yawRateValue
                  << ",\"yaw_rate_confidence_code\":" << q.yawRate.yawRateConfidence;
    }
    if (p.lowFrequencyContainer && p.lowFrequencyContainer->present == Vanetza_ITS2_LowFrequencyContainer_PR_basicVehicleContainerLowFrequency) {
        const auto& low = p.lowFrequencyContainer->choice.basicVehicleContainerLowFrequency;
        std::cout << ",\"vehicle_role_code\":" << low.vehicleRole
                  << ",\"exterior_lights_hex\":\"";
        static const char digits[] = "0123456789abcdef";
        for (std::size_t i = 0; i < low.exteriorLights.size; ++i) {
            const unsigned value = low.exteriorLights.buf[i];
            std::cout << digits[value >> 4] << digits[value & 15];
        }
        std::cout << "\",\"path_history_count\":" << low.pathHistory.list.count;
        // Dekóder číta len skutočne prítomný bod histórie z UPER paketu. Kódy presnosti vracia bez
        // prekladu na metrickú hodnotu, aby 4095 bolo možné správne rozpoznať ako unavailable.
        if (low.pathHistory.list.count > 0) {
            const auto& point = *low.pathHistory.list.array[0];
            std::cout << ",\"path_delta_latitude_e7\":" << point.pathPosition.deltaLatitude
                      << ",\"path_delta_longitude_e7\":" << point.pathPosition.deltaLongitude
                      << ",\"path_delta_altitude_cm\":" << point.pathPosition.deltaAltitude
                      << ",\"path_delta_time_10ms\":" << (point.pathDeltaTime ? *point.pathDeltaTime : -1);
        }
    }
    std::cout << "}\n";
}
