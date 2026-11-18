// Pomocný dekóder DENM cez Vanetza. Overuje význam polí v zakódovanej výstrahe; nejde o druhú
// simulačnú vetvu.
#include <vanetza/asn1/denm.hpp>
#include <vanetza/asn1/support/INTEGER.h>
#include <iostream>
#include <iomanip>
#include <string>
#include <vector>

// Rovnaký princíp pre DENM: raw bajty → Vanetza ASN.1 dekódovanie a validácia → JSON. Pri
// chýbajúcich voliteľných poliach použije normované alebo explicitne označené náhradné hodnoty;
// JSON nie je sám osebe dôkazom doručenia.
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
    vanetza::asn1::r2::Denm denm;
    if (!denm.decode(bytes.begin(), bytes.end()) || !denm.validate() ||
        denm->header.protocolVersion != 2 || denm->header.messageId != 1) return 1;
    const auto& h = denm->header;
    const auto& m = denm->denm.management;
    long detection = 0, reference = 0;
    if (asn_INTEGER2long(&m.detectionTime, &detection) ||
        asn_INTEGER2long(&m.referenceTime, &reference)) return 1;
    std::cout << std::setprecision(10)
              << "{\"protocol_version\":" << h.protocolVersion
              << ",\"message_id\":" << h.messageId
              << ",\"station_id\":" << h.stationId
              << ",\"originating_station_id\":" << m.actionId.originatingStationId
              << ",\"sequence_number\":" << m.actionId.sequenceNumber
              << ",\"detection_time_ms\":" << detection
              << ",\"reference_time_ms\":" << reference
              << ",\"validity_s\":" << (m.validityDuration ? *m.validityDuration : 600)
              << ",\"transmission_interval_ms\":" <<
                   (m.transmissionInterval ? *m.transmissionInterval : 0)
              << ",\"termination\":" << (m.termination ? *m.termination : -1)
              << ",\"station_type\":" << m.stationType
              << ",\"latitude_deg\":" << m.eventPosition.latitude / 10000000.0
              << ",\"longitude_deg\":" << m.eventPosition.longitude / 10000000.0
              << ",\"altitude_m\":" << m.eventPosition.altitude.altitudeValue / 100.0
              // Dekóder vracia aj skutočne prenesené kódy neistoty polohy a kvality udalosti, aby
              // bolo možné overiť, že DENM netvrdí nameranú presnosť.
              << ",\"position_confidence_major_code\":" << m.eventPosition.positionConfidenceEllipse.semiMajorConfidence
              << ",\"position_confidence_minor_code\":" << m.eventPosition.positionConfidenceEllipse.semiMinorConfidence
              << ",\"information_quality_code\":" << (denm->denm.situation ?
                   denm->denm.situation->informationQuality : -1)
              << ",\"cause_code\":" << (denm->denm.situation ?
                   denm->denm.situation->eventType.ccAndScc.present : 0)
              << ",\"traffic_subcause\":" << (denm->denm.situation &&
                   denm->denm.situation->eventType.ccAndScc.present ==
                       Vanetza_ITS2_CauseCodeChoice_PR_trafficCondition1 ?
                   denm->denm.situation->eventType.ccAndScc.choice.trafficCondition1 : -1)
              << ",\"detection_paths\":" << (denm->denm.location ?
                   denm->denm.location->detectionZonesToEventPosition.list.count : 0)
              << "}\n";
}
