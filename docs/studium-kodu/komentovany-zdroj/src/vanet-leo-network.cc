// Jednotný ns-3/SNS-3 engine používa ten istý profil CAM a antén ako pozemný engine, aby
// porovnanie nemenilo skryté nastavenia.
// Ground VANET and generic DVB satellite packets share one ns-3 event clock.
// RF parameters and directional queue limits come from the validated scenario.
#include <ns3/core-module.h>
#include <ns3/network-module.h>
#include <ns3/channel-list.h>
#include <ns3/wifi-module.h>
#include <ns3/mobility-module.h>
#include <ns3/internet-module.h>
#include <ns3/point-to-point-module.h>
#include <ns3/wave-module.h>
#include <ns3/buildings-module.h>
#include <ns3/propagation-module.h>
#include "ground-building-condition.h"
#include "rsu-radio-config.h"
#include <ns3/wifi-phy-state-helper.h>
#include <openssl/sha.h>
#include <vanetza/asn1/cam.hpp>
#include <vanetza/asn1/denm.hpp>
#include <vanetza/asn1/support/INTEGER.h>
#include <vanetza/asn1/packet_visitor.hpp>
#include <vanetza/btp/header.hpp>
#include <vanetza/btp/port_dispatcher.hpp>
#include <vanetza/btp/ports.hpp>
#include <vanetza/common/position_fix.hpp>
#include <vanetza/common/runtime.hpp>
#include <vanetza/common/serialization_buffer.hpp>
#include <vanetza/dcc/data_request.hpp>
#include <vanetza/dcc/interface.hpp>
#include <vanetza/geonet/data_request.hpp>
#include <vanetza/geonet/data_confirm.hpp>
#include <vanetza/geonet/router.hpp>
#include <vanetza/net/mac_address.hpp>
#include <boost/variant.hpp>
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <deque>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <numeric>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <ns3/satellite-module.h> // SNS-3 3.38 defines a global pi macro; include last.

#include "satellite-link-condition.h"
namespace n = ns3;
namespace v = vanetza;
// `ensure()` overí predpoklad a pri jeho porušení vyvolá výnimku.
static void ensure(bool okay, const char* why) { if (!okay) throw std::runtime_error(why); }
static std::string runtime_origin = "2026-10-22 12:45:00";

// Vanetza potrebuje čas a plánovač udalostí. Táto trieda ju napája na čas ns-3, aby kódovanie,
// vysielanie aj prijatie CAM/DENM patrili do jedného simulačného procesu. UTC dátum je základ
// časových polí správ; mikrosekundy ns-3 určujú poradie udalostí.
class SimulatorRuntime final : public v::Runtime {
public:
    SimulatorRuntime() : origin_(v::Clock::at(runtime_origin)) {}
    // `schedule()` preloží požiadavku Vanetza na plánovanú udalosť v hodinách ns-3.
    void schedule(v::Clock::time_point tp, const Callback& cb, const void* scope = nullptr) override {
        auto delta = std::chrono::duration_cast<std::chrono::microseconds>(tp - now()).count();
        if (delta < 0) delta = 0;
        events_.push_back({scope, n::Simulator::Schedule(n::MicroSeconds(delta), [cb, tp]() { cb(tp); })});
    }
    // `schedule()` preloží požiadavku Vanetza na plánovanú udalosť v hodinách ns-3.
    void schedule(v::Clock::duration d, const Callback& cb, const void* scope = nullptr) override {
        schedule(now() + d, cb, scope);
    }
    // `cancel()` zruší ešte nevykonané časované udalosti.
    void cancel(const void* scope) override {
        if (!scope) return;
        for (auto& e : events_) if (e.first == scope) e.second.Cancel();
    }
    // `now()` vráti aktuálny simulačný čas prevedený na čas Vanetza.
    v::Clock::time_point now() const override {
        return origin_ + v::Clock::duration(n::Simulator::Now().GetMicroSeconds());
    }
private:
    v::Clock::time_point origin_;
    std::vector<std::pair<const void*, n::EventId>> events_;
};

// Jeden Waypoint je jeden časovaný stav auta alebo RSU. Prípony v názvoch sú jednotky: `_us`
// mikrosekundy, `_m` metre, `_e7` zemepisné stupne násobené 10⁷, `_cm` centimetre, `_cmps`
// centimetre za sekundu a `_decideg` desatiny stupňa. Táto štruktúra je most medzi SUMO, rádiovým
// pohybom a obsahom CAM.
struct Waypoint {
    std::string node_id, kind;
    unsigned index, station_id;
    std::int64_t time_us;
    double x_m, y_m;
    long lat_e7, lon_e7, alt_cm, speed_cmps, heading_decideg, gdt_ms;
    long accel_dmps2, yaw_cdegps, curvature_1e4, length_dm, width_dm, lights;
};
// `tracks` mapuje ID uzla na jeho chronologický zoznam waypointov; `node_order` ďalej určuje
// poradie vytvárania ns-3 uzlov. Mapovanie ID → poloha musí byť stabilné, inak by sa CAM a
// paketové stopy priradili nesprávnemu autu alebo RSU.
static std::map<std::string, std::vector<Waypoint>> tracks;
static std::vector<std::string> node_order;
static std::string source_id, rsu_id;
static std::vector<std::string> active_rsus;
static std::string backhaul_mode = "satellite";
static bool cam_denm_mode = false;
static std::string denm_events_file, denm_target_rsu;
// Každá výstraha má samostatný zdroj a čas. Stav aktualizácie je kľúčovaný zdrojovou stanicou a
// číslom výstrahy, aby sa rovnaké čísla rôznych áut nemiešali.
struct DenmEvent {
    std::int64_t time_us;
    std::string source_id;
    unsigned sequence;
    std::string operation;
    unsigned validity_s, radius_m, repetition_ms;
};
static std::vector<DenmEvent> denm_events;
static std::string scenario_identity, run_identity;
static unsigned rsu_station_id = 0, ns3_run = 1;
static std::size_t cam_count = 0;
static std::int64_t last_cam_us = 0, cam_step_us = 0;
static std::ofstream event_trace;
static std::set<std::uint64_t> accepted_reports;
using CamKey = std::pair<unsigned, long>;
static std::map<CamKey, Waypoint> sampled_cam;
static std::map<CamKey, std::vector<std::uint8_t>> transmitted_cam;
static std::map<CamKey, std::uint64_t> cam_event_by_key, report_by_cam;
static std::map<std::uint64_t, std::uint64_t> cam_by_report;
static std::map<std::uint64_t, unsigned> station_by_report;
static std::map<std::uint64_t, std::string> rsu_by_report;
static std::map<std::uint64_t, std::string> identity_inputs;
static std::map<std::uint64_t, std::vector<std::uint8_t>> transmitted_gn;
static bool building_channel = false;
static std::string building_file;
static std::string osm_building_file;
static n::Ptr<groundradio::OSMBuildingCondition> osm_condition;
// Rovnaké argumenty menia spúšťanie CAM aj výšku uzlov v spoločnej pozemnej a satelitnej
// simulácii.
static double cam_distance_m = 4.0, cam_speed_mps = 0.5, cam_heading_deg = 4.0;
static unsigned cam_low_frequency_ms = 500, cam_tgen_max_ms = 1000, cam_periodic_repeat = 3;
static double car_antenna_height_m = 1.5, rsu_antenna_min_height_m = 5.0, rsu_roof_clearance_m = 2.0;
// Pozemný aj satelitný terminál RSU používajú rovnakú výšku antény: aspoň 5 m, na označenej budove
// strecha plus 2 m. Integrovaný ns-3 beh dostane kanál, rýchlosť, zisk a tieňovanie zo scenára.
static double radio_height(const Waypoint& w) {
    if (w.kind != "rsu") {
        const auto* profile = rsuradio::find_car(w.node_id);
        return profile ? profile->height : car_antenna_height_m;
    }
    const auto* profile = rsuradio::find(w.node_id);
    if (profile && profile->height >= 0) return profile->height;
    return std::max(rsu_antenna_min_height_m, osm_condition ? osm_condition->RoofAt(w.x_m, w.y_m) + rsu_roof_clearance_m : rsu_antenna_min_height_m);
}
static std::set<std::string> ground_off_cars, cars_only, ground_off_rsus, satellite_off_rsus;
static std::int64_t simulation_end_us = 0;
struct BuildingBox { std::string id; double xmin, xmax, ymin, ymax, zmin, zmax; };
static std::vector<BuildingBox> building_boxes;
static std::ofstream building_trace;
static std::ofstream satellite_visibility_trace;
static double satellite_mask_deg = 0.5;
static std::string satellite_terminal_config;
static std::unique_ptr<satelliteradio::Condition> satellite_condition;
// `on_native_satellite_mask_drop()` zaznamená odmietnutie satelitného linku pre elevačnú masku.
static void on_native_satellite_mask_drop(double elevation) {
    satellite_visibility_trace << n::Simulator::Now().GetMicroSeconds()
                               << ',' << std::setprecision(10) << elevation << '\n';
}
// Načíta obdĺžnikové budovy ručne zostaveného sveta. Pozemný rádiový model používa ich rozmery pri
// teste priamej viditeľnosti. Pri reálnej OSM mape sa spracúvajú polygóny zvlášť; zmena budov v
// editore sa musí premietnuť do vstupného súboru.
static void load_building_boxes(const std::string& path) {
    std::ifstream file(path);
    ensure(bool(file), "native building CSV missing");
    std::string line;
    std::getline(file, line);
    ensure(line == "id,x_min,x_max,y_min,y_max,z_min,z_max", "native building CSV header invalid");
    while (std::getline(file, line)) {
        if (line.empty()) continue;
        std::stringstream stream(line);
        std::vector<std::string> cells;
        std::string cell;
        while (std::getline(stream, cell, ',')) cells.push_back(cell);
        ensure(cells.size() == 7, "native building CSV row invalid");
        BuildingBox box{cells[0], std::stod(cells[1]), std::stod(cells[2]),
                        std::stod(cells[3]), std::stod(cells[4]),
                        std::stod(cells[5]), std::stod(cells[6])};
        ensure(box.xmin < box.xmax && box.ymin < box.ymax && box.zmin < box.zmax,
               "native building box invalid");
        building_boxes.push_back(box);
    }
    ensure(!building_boxes.empty() && building_boxes.size() <= 100,
           "native building count invalid");
}
static std::ofstream bytes_trace, mobility_trace, decoded_trace;
static std::ofstream cam_trace, phy_state_trace, dcc_trace, rx_trace, phy_drop_trace, identity_trace;
static std::ofstream selection_trace, queue_trace;
static std::ofstream satellite_ip_trace;
static std::uint64_t phy_sequence = 0;
static unsigned integrated_phy_drops = 0;
static bool dcc_enabled = false;
static double dcc_low_cbr = 0.004, dcc_high_cbr = 0.012;
static unsigned dcc_mid_ms = 250, dcc_high_ms = 500, phase_us = 1000;
static double radio_power_dbm = 20, radio_noise_figure_db = 7;
static unsigned radio_rate_mbps = 6;
static unsigned radio_channel_number = 180;
static double radio_tx_gain_dbi = 0, radio_rx_gain_dbi = 0;
static bool radio_shadowing = false;
static std::string radio_mode = "urban_los";

// `id_hex()` naformátuje identitu udalosti v šestnástkovej sústave.
static std::string id_hex(std::uint64_t id) {
    std::ostringstream out;
    out << std::hex << std::setw(16) << std::setfill('0') << id;
    return out.str();
}
// `unique_id()` vytvorí stabilnú identitu z obsahu vstupu.
static std::uint64_t unique_id(const std::string& input) {
    std::string bytes = "bp-unified-event-v1";
    bytes.push_back('\0');
    bytes += input;
    std::array<unsigned char, SHA256_DIGEST_LENGTH> hash{};
    SHA256(reinterpret_cast<const unsigned char*>(bytes.data()), bytes.size(), hash.data());
    std::uint64_t value = 0;
    for (unsigned i = 0; i < 8; ++i) value = (value << 8) | hash[i];
    ensure(identity_inputs.emplace(value, input).second, "duplicate or colliding ground radio event identity");
    return value;
}
// `cam_id()` pracuje so správou CAM.
static std::uint64_t cam_id(const Waypoint& w, unsigned sequence, std::int64_t send_us) {
    return unique_id("[\"cam\",\"" + scenario_identity + "\",\"" + run_identity + "\"," +
                     std::to_string(w.station_id) + ',' + std::to_string(sequence) + ',' +
                     std::to_string(send_us) + ',' + std::to_string(w.gdt_ms) + ']');
}
static std::map<std::pair<unsigned,unsigned>, long> denm_detection_ms;
static std::map<std::pair<unsigned,unsigned>, unsigned> denm_radius_by_action;
static std::map<unsigned,std::string> denm_origin_by_station;
// `denm_id()` odvodí identitu konkrétnej verzie výstrahy DENM.
static std::uint64_t denm_id(const v::asn1::r2::Denm& denm) {
    long reference = 0;
    ensure(asn_INTEGER2long(&denm->denm.management.referenceTime, &reference) == 0,
           "DENM reference time cannot be decoded");
    const auto& action = denm->denm.management.actionId;
    const std::string key = "denm:" + std::to_string(action.originatingStationId) + ':' +
        std::to_string(action.sequenceNumber) + ':' + std::to_string(reference);
    std::array<unsigned char, SHA256_DIGEST_LENGTH> hash{};
    SHA256(reinterpret_cast<const unsigned char*>(key.data()), key.size(), hash.data());
    std::uint64_t id = 0;
    for (unsigned i = 0; i < 8; ++i) id = (id << 8) | hash[i];
    return id;
}
// `decode_denm()` prekladá raw bajty na významové polia.
static v::asn1::r2::Denm decode_denm(const std::vector<std::uint8_t>& raw) {
    v::asn1::r2::Denm denm;
    ensure(denm.decode(raw) && denm.validate() &&
           denm->header.protocolVersion == 2 && denm->header.messageId == 1,
           "native DENM UPER decode or constraint failure");
    return denm;
}
static long its_milliseconds(std::int64_t now_us) {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
        v::Clock::at(runtime_origin).time_since_epoch()).count() + now_us / 1000;
}
// Tu sa z udalosti scenára zostaví sémantický ETSI DENM. Dôležité sú identita udalosti, čas
// detekcie, platnosť, poloha a opakovanie; Vanetza následne vytvorí UPER bajty. To, že objekt DENM
// vznikol, ešte neznamená úspešný rádiový prenos.
static v::asn1::r2::Denm make_denm(const Waypoint& w, const Waypoint& previous,
                                   const DenmEvent& event) {
    v::asn1::r2::Denm denm;
    denm->header.protocolVersion = 2;
    denm->header.messageId = 1;
    denm->header.stationId = w.station_id;
    auto& management = denm->denm.management;
    management.actionId.originatingStationId = w.station_id;
    management.actionId.sequenceNumber = event.sequence;
    const auto detection = denm_detection_ms.emplace(std::make_pair(w.station_id,event.sequence),
        its_milliseconds(event.time_us)).first->second;
    ensure(asn_long2INTEGER(&management.detectionTime, detection) == 0 &&
           asn_long2INTEGER(&management.referenceTime, its_milliseconds(event.time_us)) == 0,
           "DENM ITS timestamp construction failed");
    if (event.operation == "cancel") {
        management.termination = v::asn1::allocate<Vanetza_ITS2_Termination_t>();
        *management.termination = Vanetza_ITS2_Termination_isCancellation;
    }
    auto& p = management.eventPosition;
    p.latitude = w.lat_e7;
    p.longitude = w.lon_e7;
    p.positionConfidenceEllipse.semiMajorConfidence = Vanetza_ITS2_SemiAxisLength_unavailable;
    p.positionConfidenceEllipse.semiMinorConfidence = Vanetza_ITS2_SemiAxisLength_unavailable;
    p.positionConfidenceEllipse.semiMajorOrientation = Vanetza_ITS2_Wgs84AngleValue_unavailable;
    p.altitude.altitudeValue = w.alt_cm;
    p.altitude.altitudeConfidence = Vanetza_ITS2_AltitudeConfidence_unavailable;
    management.stationType = Vanetza_ITS2_TrafficParticipantType_passengerCar;
    management.validityDuration = v::asn1::allocate<Vanetza_ITS2_DeltaTimeSecond_t>();
    *management.validityDuration = event.validity_s;
    if (event.repetition_ms) {
        management.transmissionInterval =
            v::asn1::allocate<Vanetza_ITS2_DeltaTimeMilliSecondPositive_t>();
        *management.transmissionInterval = event.repetition_ms;
    }
    denm->denm.situation = v::asn1::allocate<Vanetza_ITS2_SituationContainer_t>();
    denm->denm.situation->informationQuality = 0;
    denm->denm.situation->eventType.ccAndScc.present =
        Vanetza_ITS2_CauseCodeChoice_PR_trafficCondition1;
    denm->denm.situation->eventType.ccAndScc.choice.trafficCondition1 =
        Vanetza_ITS2_TrafficConditionSubCauseCode_trafficJam;
    denm->denm.location = v::asn1::allocate<Vanetza_ITS2_LocationContainer_t>();
    auto* path = v::asn1::allocate<Vanetza_ITS2_Path_t>();
    auto* point = v::asn1::allocate<Vanetza_ITS2_PathPoint_t>();
    point->pathPosition.deltaLatitude = std::clamp(previous.lat_e7 - w.lat_e7, -131071L, 131071L);
    point->pathPosition.deltaLongitude = std::clamp(previous.lon_e7 - w.lon_e7, -131071L, 131071L);
    point->pathPosition.deltaAltitude = std::clamp(previous.alt_cm - w.alt_cm, -127L, 127L);
    ensure(ASN_SEQUENCE_ADD(&path->list, point) == 0 &&
           ASN_SEQUENCE_ADD(&denm->denm.location->detectionZonesToEventPosition.list, path) == 0,
           "DENM detection zone path allocation failed");
    std::string error;
    ensure(denm.validate(error), error.c_str());
    return denm;
}
// `report_id()` odvodí identitu hlásenia od pôvodného CAM.
static std::uint64_t report_id(std::uint64_t cam, unsigned station) {
    return unique_id("[\"report\",\"" + scenario_identity + "\",\"" + run_identity + "\",\"" +
                     id_hex(cam) + "\"," + std::to_string(station) + ",0]");
}
// `response_id()` odvodí identitu odpovede od prijatého hlásenia.
static std::uint64_t response_id(std::uint64_t report, unsigned recipient) {
    return unique_id("[\"response\",\"" + scenario_identity + "\",\"" + run_identity + "\",\"" +
                     id_hex(report) + "\"," + std::to_string(recipient) + ",0]");
}

// Socket je koncový bod IP/UDP v ns-3. Tieto mapy držia jeden alebo viac socketov podľa RSU a
// smeru správy. `std::map` umožňuje nájsť správny socket podľa ID uzla; `Ptr<Socket>` znamená, že
// sa posiela cez natívny sieťový model.
static std::map<std::string, n::Ptr<n::Socket>> report_sockets;
static n::Ptr<n::Socket> satellite_socket;
static n::Ptr<n::Socket> gateway_ack_socket, ut_lan_ack_socket, ground_socket;
static std::map<std::string, n::Ptr<n::Socket>> rsu_satellite_sockets, rsu_lan_ack_sockets;
static std::map<std::string, n::Ptr<n::NetDevice>> rsu_ocb_devices;
static std::map<unsigned, n::Address> car_ocb_addresses;
static std::map<std::string, n::Ipv4Address> ut_lan_addresses, rsu_lan_addresses;
static n::Ipv4Address ut_sat_address, gateway_address, ut_ground_address, gateway_ground_address;
static std::map<std::string, n::Ipv4Address> rsu_sat_addresses;
static std::vector<std::string> terminal_rsus;
static bool block_satellite = false;
static bool no_return_route = false;
static std::string handover_case = "stay";
static std::string handover_state = "connected_old";
static std::map<std::string, std::string> handover_states;
static std::set<std::string> handover_probe_gateway, handover_probe_returned;
static unsigned handover_target_sat = 0, handover_beam = 30;
static std::int64_t handover_request_us = 11000000;
static bool probe_reached_gateway = false, probe_returned = false;
static unsigned pending_report_drops = 0;
static std::set<std::uint64_t> pending_dropped_ids;
static std::map<unsigned, unsigned> sat_node_index;
static std::set<std::uint64_t> satellite_forward_isl_drops, satellite_reverse_isl_drops;
static unsigned satellite_other_forward_drops = 0, satellite_other_reverse_drops = 0;
static bool satellite_burst = false;
static std::int64_t satellite_burst_release_us = 13500000;
static std::vector<n::Ptr<n::Packet>> satellite_held_reports;
static double satellite_ut_power_dbw = 4.0;
static std::uint64_t satellite_forward_bps = 1000000000ULL, satellite_reverse_bps = 1000000000ULL;
static unsigned satellite_forward_queue_packets = 100, satellite_reverse_queue_packets = 100;
static std::int64_t satellite_apply_us = 12500000;
static unsigned reports_created = 0, reports_offered = 0, ut_received = 0,
                satellite_offered = 0, server_accepted = 0, server_rejected = 0;
static unsigned isl_report_receives = 0, isl_ack_receives = 0, gateway_ack_sent = 0,
                ut_ack_received = 0, rsu_ack_received = 0, car_i2v_received = 0;
static unsigned wifi_phy_drops = 0, lan_drops = 0;
static constexpr std::uint16_t report_port = 45000;
static constexpr std::uint16_t ack_port = 45001;
static constexpr std::uint16_t denm_uplink_port = 45002;
static constexpr std::uint16_t denm_downlink_port = 45003;
static std::map<std::string, n::Ptr<n::Socket>> denm_rsu_uplink_sockets,
    denm_ut_sat_sockets, denm_gw_downlink_sockets, denm_ut_lan_sockets;
static n::Ptr<n::Socket> denm_gateway_socket;
static std::map<std::string, n::Ipv4Address> denm_ut_sources;
class Station;
static std::map<std::string, Station*> denm_stations;
static std::map<std::string, std::set<std::uint64_t>> denm_sat_sent;
static constexpr std::uint16_t i2v_ethertype = 0x88B5;
static std::map<std::uint64_t, std::vector<std::uint8_t>> created_reports;
static unsigned forward_queue_capacity = 512, reverse_queue_capacity = 512;
static unsigned forward_service_us = 1000, reverse_service_us = 1000;
static unsigned forward_queue_drops = 0, reverse_queue_drops = 0;
static std::set<std::uint64_t> forward_dropped_ids, reverse_dropped_ids;
static std::deque<std::uint64_t> forward_queue, reverse_queue;
static bool forward_service_scheduled = false, reverse_service_scheduled = false;
static void process_server_report(const std::vector<std::uint8_t>& report);
static void enqueue_reverse(std::uint64_t id);
static void service_forward();
static void service_reverse();

// Waypoints sú časované polohy zo SUMO a statické polohy RSU. Táto funkcia načíta presne tie
// súradnice, z ktorých sa aktualizuje ns-3 MobilityModel aj CAM. Pri obhajobe oddeľ vstupný pohyb
// auta od účinku prijatej správy: prijatá DENM trasu auta automaticky nemení.
static void load_waypoints(const std::string& path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("v2 waypoint CSV absent: " + path);
    std::string line;
    std::getline(in, line);
    ensure(line == "node_id,station_id,kind,index,time_us,utc,x_m,y_m,latitude_e7,longitude_e7,altitude_cm,speed_cmps,heading_decideg,generation_delta_ms,acceleration_dmps2,yaw_rate_cdegps,curvature_1e4,vehicle_length_dm,vehicle_width_dm,exterior_lights_bits", "wrong waypoint header");
    while (std::getline(in, line)) {
        if (line.empty()) continue;
        std::stringstream ss(line);
        std::vector<std::string> c;
        std::string token;
        while (std::getline(ss, token, ',')) c.push_back(token);
        ensure(c.size() == 20 && !c[0].empty() && (c[2] == "car" || c[2] == "rsu"), "invalid waypoint row");
        Waypoint w{c[0], c[2], static_cast<unsigned>(std::stoul(c[3])), static_cast<unsigned>(std::stoul(c[1])),
                   std::stoll(c[4]), std::stod(c[6]), std::stod(c[7]), std::stol(c[8]),
                   std::stol(c[9]), std::stol(c[10]), std::stol(c[11]), std::stol(c[12]), std::stol(c[13]),
                   std::stol(c[14]), std::stol(c[15]), std::stol(c[16]), std::stol(c[17]),
                   std::stol(c[18]), std::stol(c[19])};
        auto& track = tracks[w.node_id];
        if (track.empty()) node_order.push_back(w.node_id);
        ensure(w.index == track.size() && w.station_id == 1001U + node_order.size() - 1 &&
               (track.empty() || w.time_us > track.back().time_us), "v3 samples not ordered");
        track.push_back(w);
        if (w.kind == "car")
            ensure(sampled_cam.emplace(CamKey{w.station_id, w.gdt_ms}, w).second,
                   "duplicate station/GDT within ground radio sample window");
    }
    ensure(node_order.size() >= 3 &&
           node_order.front() == source_id && node_order.back() == rsu_id &&
           tracks.at(source_id).front().kind == "car" && tracks.at(rsu_id).front().kind == "rsu",
           "backhaul needs source car first and primary RSU last");
    for (const auto& id : node_order)
        if (tracks.at(id).front().kind == "rsu") active_rsus.push_back(id);
    ensure(!active_rsus.empty(), "backhaul needs at least one active RSU bound to the fixed UT");
    cam_count = tracks.at(source_id).size();
    ensure(cam_count >= 20 && cam_count <= 1200, "simulator sample count outside 20..1200 range");
    rsu_station_id = tracks.at(rsu_id).front().station_id;
    last_cam_us = tracks.at(source_id).back().time_us;
    if (cam_count > 1) {
        cam_step_us = tracks.at(source_id)[1].time_us - tracks.at(source_id)[0].time_us;
        ensure(cam_step_us == 100000, "ground radio requires ground model 100ms FCD samples");
    }
    for (std::size_t i = 1; i < cam_count; ++i)
        ensure(tracks.at(source_id)[i].time_us - tracks.at(source_id)[i-1].time_us == cam_step_us,
               "v3 CAM schedule is not uniform");
    ensure(sampled_cam.size() >= 2 * cam_count, "ground radio needs multiple CAM senders");
    for (const auto& id : node_order) {
        ensure(tracks.at(id).size() == cam_count, "v3 waypoint count differs by radio node");
        for (std::size_t i = 0; i < cam_count; ++i)
            ensure(tracks.at(id)[i].time_us == tracks.at(source_id)[i].time_us &&
                   tracks.at(id)[i].gdt_ms == tracks.at(source_id)[i].gdt_ms,
                   "radio node waypoint timestamps differ");
    }
}

// `policy_ids()` načíta zoznam uzlov, na ktoré sa vzťahuje vybraná komunikačná politika.
static std::set<std::string> policy_ids(const char* key, const char* kind) {
    std::set<std::string> ids;
    const char* raw = std::getenv(key);
    if (!raw || !*raw) return ids;
    std::stringstream stream(raw);
    std::string id;
    while (std::getline(stream, id, ',')) {
        ensure(tracks.count(id) && tracks.at(id).front().kind == kind,
               "native policy node absent or wrong kind");
        ensure(ids.insert(id).second, "duplicate native policy node");
    }
    return ids;
}

// `address_of()` získa MAC adresu ns-3 sieťového zariadenia.
static v::MacAddress address_of(n::Ptr<n::NetDevice> dev) {
    std::ostringstream out;
    out << n::Mac48Address::ConvertFrom(dev->GetAddress());
    v::MacAddress address;
    ensure(v::parse_mac_address(out.str(), address), "cannot parse ns-3 MAC");
    return address;
}

// `hex_bytes()` prevedie raw bajty na čitateľný hexadecimálny text.
static std::string hex_bytes(const std::vector<std::uint8_t>& bytes) {
    static constexpr char digits[] = "0123456789abcdef";
    std::string out;
    for (auto b : bytes) { out += digits[b >> 4]; out += digits[b & 15]; }
    return out;
}

static void log_bytes(const std::string& stage, const std::string& node_id,
                      std::uint64_t id, const std::vector<std::uint8_t>& bytes) {
    bytes_trace << stage << ',' << node_id << ',' << std::hex << std::setw(16) << std::setfill('0') << id
                << std::dec << ',' << n::Simulator::Now().GetMicroSeconds() << ','
                << bytes.size() << ',' << hex_bytes(bytes) << '\n';
}
static void log_event(const std::string& stage, const std::string& node_id,
                      std::uint64_t id, const std::string& reason = "none") {
    event_trace << std::hex << std::setw(16) << std::setfill('0') << id << std::dec
                << ',' << stage << ',' << node_id << ','
                << n::Simulator::Now().GetMicroSeconds() << ',' << reason << '\n';
}

// `packet_bytes()` skopíruje bajty z objektu ns-3 Packet na ďalšiu kontrolu.
static std::vector<std::uint8_t> packet_bytes(n::Ptr<const n::Packet> packet) {
    std::vector<std::uint8_t> bytes(packet->GetSize());
    if (!bytes.empty()) packet->CopyData(bytes.data(), bytes.size());
    return bytes;
}
// SatNetDevice::Tx ešte nesie celý IPv4/UDP datagram. Jeho ns-3 UID je totožné
// s UID v SNS-3 PacketTrace, takže môžeme zviazať PHY kroky s konkrétnym DENM.
// SatNetDevice poskytuje pri odoslaní IP/UDP datagram ešte s pôvodným ns-3 packet UID. Kód overí
// port DENM, dekóduje jeho obsah a zapíše dvojicu UID a aplikačné ID. V SNS-3 PacketTrace sa to
// isté UID objaví na UT, satelite a bráne; tak vzniká dokazateľná väzba bez vlastného modelu
// prenosu.
static void on_satellite_ip_tx(std::string node_type, unsigned node_id,
                               n::Ptr<const n::Packet> packet) {
    const auto bytes = packet_bytes(packet);
    if (bytes.size() < 28 || bytes[0] >> 4 != 4) return;
    const std::size_t ip_header = (bytes[0] & 15) * 4;
    if (ip_header < 20 || bytes.size() < ip_header + 8 || bytes[9] != 17 ||
        (bytes[6] & 0x1f) || bytes[7]) return;
    const unsigned destination_port = (unsigned(bytes[ip_header + 2]) << 8) |
                                       bytes[ip_header + 3];
    if (destination_port != denm_uplink_port && destination_port != denm_downlink_port) return;
    const unsigned udp_length = (unsigned(bytes[ip_header + 4]) << 8) |
                                bytes[ip_header + 5];
    ensure(udp_length >= 8 && ip_header + udp_length <= bytes.size(),
           "satellite DENM UDP length invalid");
    const std::vector<std::uint8_t> payload(bytes.begin() + ip_header + 8,
        bytes.begin() + ip_header + udp_length);
    const auto id = denm_id(decode_denm(payload));
    satellite_ip_trace << packet->GetUid() << ',' << id_hex(id) << ','
        << node_type << ',' << node_id << ','
        << (destination_port == denm_uplink_port ? "RTN" : "FWD") << ','
        << n::Simulator::Now().GetMicroSeconds() << ',' << bytes.size() << ','
        << hex_bytes(bytes) << '\n';
}
static std::uint64_t read_u64(const std::vector<std::uint8_t>& bytes, std::size_t offset);
static bool on_isl_report(n::Ptr<n::NetDevice> device, n::Ptr<const n::Packet> packet,
                          std::uint16_t protocol, const n::Address&, const n::Address&,
                          n::NetDevice::PacketType) {
    const auto bytes = packet_bytes(packet);
    const std::array<std::uint8_t, 4> magic{'I', 'C', 'B', '1'};
    if (std::search(bytes.begin(), bytes.end(), magic.begin(), magic.end()) != bytes.end()) {
        ++isl_report_receives;
        auto isl = n::DynamicCast<n::PointToPointIslNetDevice>(device);
        ensure(isl && sat_node_index.count(device->GetNode()->GetId()) &&
               sat_node_index.count(isl->GetDestinationNode()->GetId()),
               "handover ISL device lacks satellite index");
        std::cout << "HANDOVER_ISL_REPORT_HOP=" << sat_node_index.at(device->GetNode()->GetId())
                  << "," << sat_node_index.at(isl->GetDestinationNode()->GetId())
                  << "," << n::Simulator::Now().GetMicroSeconds() << '\n';
        std::cout << "ISL_REPORT_RX_US=" << n::Simulator::Now().GetMicroSeconds()
                  << ",sat_node=" << device->GetNode()->GetId()
                  << ",protocol=" << protocol << ",bytes=" << bytes.size() << '\n';
        std::cout << "ISL_IP_PACKET_HEX=" << hex_bytes(bytes) << '\n';
    }
    const std::array<std::uint8_t, 4> ack_magic{'G', 'R', 'A', '1'};
    if (std::search(bytes.begin(), bytes.end(), ack_magic.begin(), ack_magic.end()) != bytes.end()) {
        ++isl_ack_receives;
        auto isl = n::DynamicCast<n::PointToPointIslNetDevice>(device);
        ensure(isl && sat_node_index.count(device->GetNode()->GetId()) &&
               sat_node_index.count(isl->GetDestinationNode()->GetId()),
               "handover reverse ISL device lacks satellite index");
        std::cout << "HANDOVER_ISL_ACK_HOP=" << sat_node_index.at(device->GetNode()->GetId())
                  << "," << sat_node_index.at(isl->GetDestinationNode()->GetId())
                  << "," << n::Simulator::Now().GetMicroSeconds() << '\n';
        std::cout << "ISL_ACK_RX_US=" << n::Simulator::Now().GetMicroSeconds()
                  << ",sat_node=" << device->GetNode()->GetId()
                  << ",protocol=" << protocol << ",bytes=" << bytes.size() << '\n';
        std::cout << "ISL_ACK_IP_PACKET_HEX=" << hex_bytes(bytes) << '\n';
    }
    return true;
}
static std::pair<std::string, std::uint64_t> satellite_packet_kind(const std::vector<std::uint8_t>& raw) {
    for (const auto& [magic, kind] : {std::pair<std::string,std::string>{"ICB1", "REPORT"},
                                     {"GRA1", "ACK"}}) {
        auto found = std::search(raw.begin(), raw.end(), magic.begin(), magic.end());
        if (found != raw.end() && std::distance(found, raw.end()) >= 13)
            return {kind, read_u64(std::vector<std::uint8_t>(found, raw.end()), 5)};
    }
    return {"OTHER", 0};
}
static void satellite_queue_packet(const std::string& operation, const std::string& direction,
                            const std::string& edge, n::Ptr<const n::Packet> packet) {
    auto raw = packet_bytes(packet);
    auto [kind, id] = satellite_packet_kind(raw);
    log_bytes("SATELLITE_ISL_QUEUE_" + operation + "_" + kind + "_" + direction,
              edge, id, raw);
    if (operation == "DROP") {
        if (kind == "REPORT") {
            ensure(satellite_forward_isl_drops.insert(id).second, "duplicate satellite transport report queue drop");
            log_event("dropped", edge, id, "isl_forward_queue_full");
        } else if (kind == "ACK") {
            ensure(satellite_reverse_isl_drops.insert(id).second, "duplicate satellite transport reply queue drop");
            log_event("dropped", edge, id, "isl_reverse_queue_full");
        } else if (direction == "forward") ++satellite_other_forward_drops;
        else ++satellite_other_reverse_drops;
    }
}
// Táto spätná väzba prichádza z Wi-Fi PHY ns-3, nie z vlastného odhadu doručenia. Strata a jej
// dôvod sa zapisujú do raw stopy. Očakávaný prijímateľ sa musí potvrdiť na prijímacej strane;
// samotné odoslanie nie je dôkazom doručenia.
static void on_wifi_phy_drop(const std::string& node_id, n::Ptr<const n::Packet> packet,
                             n::WifiPhyRxfailureReason reason) {
    ++wifi_phy_drops;
    auto bytes = packet_bytes(packet);
    std::uint64_t id = 0;
    for (const auto& [candidate, wire] : transmitted_gn)
        if (std::search(bytes.begin(), bytes.end(), wire.begin(), wire.end()) != bytes.end()) {
            id = candidate;
            break;
        }
    log_bytes("WIFI_PHY_RX_DROP_REASON_" + std::to_string(static_cast<int>(reason)),
              node_id, id, bytes);
}
// `on_lan_drop()` zapíše stratu rámca na drôtovom prepojení RSU a terminálu.
static void on_lan_drop(const std::string& stage, n::Ptr<const n::Packet> packet) {
    ++lan_drops;
    auto bytes = packet_bytes(packet);
    std::uint64_t id = 0;
    for (const auto& magic : {std::string("ICB1"), std::string("GRA1")}) {
        auto start = std::search(bytes.begin(), bytes.end(), magic.begin(), magic.end());
        if (start != bytes.end() && std::distance(start, bytes.end()) >= 13)
            id = read_u64(std::vector<std::uint8_t>(start, bytes.end()), 5);
    }
    log_bytes(stage, "lan", id, bytes);
}
// `append_u64()` zapíše 64-bitové číslo do výstupných bajtov.
static void append_u64(std::vector<std::uint8_t>& bytes, std::uint64_t number) {
    for (int shift = 56; shift >= 0; shift -= 8) bytes.push_back((number >> shift) & 0xff);
}
// `read_u64()` prečíta 64-bitové číslo z raw bajtov.
static std::uint64_t read_u64(const std::vector<std::uint8_t>& bytes, std::size_t offset) {
    ensure(bytes.size() >= offset + 8, "short report number");
    std::uint64_t value = 0;
    for (std::size_t i = 0; i < 8; ++i) value = (value << 8) | bytes[offset + i];
    return value;
}
// `sha256()` vypočíta kontrolný odtlačok obsahu pomocou SHA-256.
static std::array<std::uint8_t, SHA256_DIGEST_LENGTH> sha256(const std::vector<std::uint8_t>& bytes) {
    std::array<std::uint8_t, SHA256_DIGEST_LENGTH> hash{};
    SHA256(bytes.data(), bytes.size(), hash.data());
    return hash;
}
// ICB1 is an experimental application report derived from the actual RSU CAM reception.
// It is not a Globalstar terminal payload or a claimed operator protocol.
// RSU po prijatí CAM vytvára nadväzujúcu aplikačnú správu pre chrbticovú vetvu. Identita a hash
// pôvodných CAM bajtov umožňujú verifieru dokázať pôvod správy. Je to experimentálny formát, nie
// súčasť normy CAM.
static std::vector<std::uint8_t> make_report(const std::vector<std::uint8_t>& cam, std::uint64_t id) {
    ensure(cam.size() >= 41 && cam.size() <= 255, "unexpected CAM size at RSU");
    std::vector<std::uint8_t> report{'I', 'C', 'B', '1', 1};
    append_u64(report, id);
    append_u64(report, n::Simulator::Now().GetMicroSeconds());
    report.push_back(0);
    report.push_back(static_cast<std::uint8_t>(cam.size()));
    auto hash = sha256(cam);
    report.insert(report.end(), hash.begin(), hash.end());
    report.insert(report.end(), cam.begin(), cam.end());
    ensure(report.size() == 55 + cam.size(), "unexpected ground radio ICB1 size");
    return report;
}
static bool cam_matches(const v::asn1::r2::Cam& cam, const Waypoint& w);
// `valid_report()` skontroluje štruktúru a pôvod experimentálneho hlásenia.
static bool valid_report(const std::vector<std::uint8_t>& report) {
    if ((report.size() != 96 && report.size() != 98) ||
        std::string(report.begin(), report.begin() + 4) != "ICB1" ||
        report[4] != 1 || report[21] != 0 || report[22] != report.size() - 55 ||
        read_u64(report, 13) > static_cast<std::uint64_t>(n::Simulator::Now().GetMicroSeconds())) return false;
    std::vector<std::uint8_t> cam(report.begin() + 55, report.end());
    auto hash = sha256(cam);
    if (!std::equal(hash.begin(), hash.end(), report.begin() + 23)) return false;
    v::asn1::r2::Cam decoded;
    if (!decoded.decode(cam) || !decoded.validate()) return false;
    const CamKey key{static_cast<unsigned>(decoded->header.stationId),
                     static_cast<long>(decoded->cam.generationDeltaTime)};
    auto found = sampled_cam.find(key);
    auto observed = transmitted_cam.find(key);
    auto report_identity = report_by_cam.find(key);
    return found != sampled_cam.end() && observed != transmitted_cam.end() &&
           report_identity != report_by_cam.end() && observed->second == cam &&
           read_u64(report, 5) == report_identity->second && cam_matches(decoded, found->second);
}
// `make_ack()` zostaví odpoveď brány na prijaté hlásenie.
static std::vector<std::uint8_t> make_ack(const std::vector<std::uint8_t>& report) {
    ensure(valid_report(report), "GRA1 source ICB1 invalid");
    std::vector<std::uint8_t> ack{'G','R','A','1',1};
    append_u64(ack, read_u64(report, 5));
    auto digest = sha256(report);
    ack.insert(ack.end(), digest.begin(), digest.end());
    ack.push_back(0);
    ensure(ack.size() == 46, "GRA1 size changed");
    return ack;
}
// `valid_ack()` skontroluje štruktúru a pôvod odpovede z brány.
static bool valid_ack(const std::vector<std::uint8_t>& ack) {
    if (ack.size() != 46 || std::string(ack.begin(), ack.begin()+4) != "GRA1" ||
        ack[4] != 1 || ack[45] != 0) return false;
    auto id = read_u64(ack, 5);
    auto found = created_reports.find(id);
    if (found == created_reports.end()) return false;
    auto digest = sha256(found->second);
    return std::equal(digest.begin(), digest.end(), ack.begin()+13);
}
// `make_i2v1()` zostaví spätnú správu určenú pre pozemnú vetvu.
static std::vector<std::uint8_t> make_i2v1(const std::vector<std::uint8_t>& ack) {
    ensure(valid_ack(ack), "I2V1 source GRA1 invalid");
    std::vector<std::uint8_t> msg{'I','2','V','1',1};
    append_u64(msg, read_u64(ack, 5));
    const auto station = station_by_report.at(read_u64(ack, 5));
    for (int shift = 24; shift >= 0; shift -= 8)
        msg.push_back((station >> shift) & 0xff);
    msg.insert(msg.end(), ack.begin()+13, ack.begin()+45);
    msg.push_back(ack[45]);
    ensure(msg.size() == 50, "I2V1 size changed");
    return msg;
}
// `valid_i2v1()` skontroluje rámec spätnej správy smerom k autu.
static bool valid_i2v1(const std::vector<std::uint8_t>& msg) {
    if (msg.size() != 50 || std::string(msg.begin(), msg.begin()+4) != "I2V1" ||
        msg[4] != 1 || msg[49] != 0) return false;
    auto id = read_u64(msg, 5);
    auto found = created_reports.find(id);
    if (found == created_reports.end()) return false;
    const auto station = station_by_report.at(id);
    if (((static_cast<unsigned>(msg[13]) << 24) | (static_cast<unsigned>(msg[14]) << 16) |
          (static_cast<unsigned>(msg[15]) << 8) | msg[16]) != station) return false;
    auto digest = sha256(found->second);
    return std::equal(digest.begin(), digest.end(), msg.begin()+17);
}
// `bind_udp()` vytvorí a pripojí ns-3 UDP socket k uzlu a adrese.
static n::Ptr<n::Socket> bind_udp(n::Ptr<n::Node> node, n::Ipv4Address address, std::uint16_t port) {
    auto socket = n::Socket::CreateSocket(node, n::UdpSocketFactory::GetTypeId());
    ensure(socket->Bind(n::InetSocketAddress(address, port)) == 0, "UDP bind failed");
    return socket;
}
// Prijímací socket terminálu RSU pre správy zo siete. Spracovanie číta skutočné prijaté ns-3
// pakety a zapisuje ich pôvod; toto miesto je dôležité pri dokazovaní, že sa správa cez satelit
// skutočne vrátila, namiesto vyhlásenia doručenia vlastným plánovačom.
static void ut_receive(std::string owner_rsu, n::Ptr<n::Socket> sink) {
    n::Ptr<n::Packet> packet;
    while ((packet = sink->Recv())) {
        auto report = packet_bytes(packet);
        auto id = report.size() >= 13 ? read_u64(report, 5) : 0;
        ensure(valid_report(report), "UT LAN ICB1 content invalid");
        ensure(rsu_by_report.at(id) == owner_rsu, "RSU report reached another satellite terminal");
        ++ut_received;
        log_bytes("UT_LAN_REPORT_RX", "ut-user", id, report);
        const auto owner_state = handover_states.count(owner_rsu) ?
            handover_states.at(owner_rsu) : handover_state;
        if (backhaul_mode == "satellite" &&
            (owner_state == "pending" || owner_state == "await_probe")) {
            ++pending_report_drops;
            pending_dropped_ids.insert(id);
            log_bytes("HANDOVER_PENDING_NO_QUEUE_DROP", "ut-user", id, report);
            log_event("dropped", "ut-user", id, "handover_pending");
            continue;
        }
        if (!block_satellite) {
            if (satellite_burst && backhaul_mode == "satellite") {
                ensure(n::Simulator::Now().GetMicroSeconds() < satellite_burst_release_us,
                       "satellite transport report arrived after declared burst release");
                satellite_held_reports.push_back(packet->Copy());
                log_bytes("SATELLITE_UT_APP_QUEUE_ENQUEUE", "ut-user", id, report);
                if (satellite_held_reports.size() == 1)
                    n::Simulator::Schedule(n::MicroSeconds(satellite_burst_release_us) -
                                           n::Simulator::Now(), [] {
                        for (auto held : satellite_held_reports) {
                            auto raw = packet_bytes(held);
                            auto held_id = read_u64(raw, 5);
                            ensure(rsu_satellite_sockets.at(rsu_by_report.at(held_id))->SendTo(held, 0,
                                   n::InetSocketAddress(gateway_address, report_port)) ==
                                   static_cast<int>(raw.size()), "satellite transport real ICB1 burst send failed");
                            ++satellite_offered;
                            log_bytes("UT_SAT_REPORT_TX", "ut-user", held_id, raw);
                            log_event("sent", "ut-user", held_id);
                        }
                        satellite_held_reports.clear();
                    });
                continue;
            }
            auto destination = backhaul_mode == "ground" ? gateway_ground_address : gateway_address;
            auto socket = backhaul_mode == "ground" ? ground_socket : rsu_satellite_sockets.at(owner_rsu);
            ensure(socket->SendTo(packet, 0, n::InetSocketAddress(destination, report_port)) ==
                   static_cast<int>(report.size()), "UT backhaul report send failed");
            ++satellite_offered;
            log_bytes(backhaul_mode == "ground" ? "UT_GROUND_REPORT_TX" : "UT_SAT_REPORT_TX",
                      "ut-user", id, report);
            log_event("sent", "ut-user", id);
        } else {
            log_event("dropped", "ut-user", id, "experiment_satellite_gate");
        }
    }
}
// Brána overí obsah hlásenia pochádzajúceho od RSU a rozhodne o odpovedi. Sleduj identifikátor
// hlásenia a porovnanie bajtov: na nich stojí dôkaz celej cesty auto → RSU → terminál → SNS-3 →
// brána.
static void process_server_report(const std::vector<std::uint8_t>& report) {
    auto id = report.size() >= 13 ? read_u64(report, 5) : 0;
    const std::string server = backhaul_mode == "local" ? "rsu-app" : "gateway-user";
    log_bytes("REMOTE_APP_REPORT_RX", server, id, report);
    if (!valid_report(report)) {
        ++server_rejected;
        log_bytes("GATEWAY_REJECT", server, id, report);
        return;
    }
    ensure(accepted_reports.insert(id).second, "duplicate remote application report");
    ++server_accepted;
    log_bytes("GATEWAY_ACCEPT", server, id, report);
    log_event("received", server, id, "remote_report");
    if (no_return_route) {
        log_bytes("GATEWAY_RETURN_ROUTE_BLOCKED", server, id, report);
        log_event("dropped", server, id, "no_return_route");
        return;
    }
    auto ack = make_ack(report);
    const auto reply = response_id(id, station_by_report.at(id));
    identity_trace << "response," << id_hex(reply) << ',' << id_hex(id) << ','
                   << station_by_report.at(id) << ",0,"
                   << n::Simulator::Now().GetMicroSeconds() << ",0\n";
    ++gateway_ack_sent;
    log_bytes("GATEWAY_GRA1_TX", server, id, ack);
    if (backhaul_mode == "local") {
        ++rsu_ack_received;
        log_bytes("RSU_GRA1_RX", rsu_by_report.at(id), id, ack);
        enqueue_reverse(id);
    } else {
        auto destination = backhaul_mode == "ground" ? ut_ground_address : rsu_sat_addresses.at(rsu_by_report.at(id));
        ensure(gateway_ack_socket->SendTo(n::Create<n::Packet>(ack.data(), ack.size()), 0,
                   n::InetSocketAddress(destination, ack_port)) == static_cast<int>(ack.size()),
               "GRA1 backhaul return send failed");
    }
}
// `server_receive()` spracuje paket skutočne prijatý bránovým socketom.
static void server_receive(n::Ptr<n::Socket> sink) {
    n::Ptr<n::Packet> packet;
    n::Address peer;
    while ((packet = sink->RecvFrom(peer))) {
        auto report = packet_bytes(packet);
        if (report == std::vector<std::uint8_t>{'P','3','P','R'}) {
            probe_reached_gateway = true;
            const auto source = n::InetSocketAddress::ConvertFrom(peer).GetIpv4();
            auto owner = std::find_if(rsu_sat_addresses.begin(), rsu_sat_addresses.end(),
                [source](const auto& item) { return item.second == source; });
            ensure(owner != rsu_sat_addresses.end(), "handover probe source is not an RSU terminal");
            handover_probe_gateway.insert(owner->first);
            std::cout << "HANDOVER_PROBE_GATEWAY_RX_US=" << n::Simulator::Now().GetMicroSeconds()
                      << " RSU=" << owner->first << '\n';
            if (handover_case != "attach_failed") {
                const std::uint8_t ack[] = {'P','3','P','A'};
                ensure(gateway_ack_socket->SendTo(n::Create<n::Packet>(ack, sizeof(ack)), 0,
                           n::InetSocketAddress(source, ack_port)) == 4,
                       "handover probe return send failed");
            }
            continue;
        }
        process_server_report(report);
    }
}
// `ut_ack_receive()` spracuje odpoveď prijatú používateľským satelitným terminálom.
static void ut_ack_receive(std::string owner_rsu, n::Ptr<n::Socket> sink) {
    n::Ptr<n::Packet> packet;
    while ((packet = sink->Recv())) {
        auto ack = packet_bytes(packet);
        if (ack == std::vector<std::uint8_t>{'P','3','P','A'}) {
            auto& state = handover_states.at(owner_rsu);
            if (state != "await_probe") {std::cout<<"SIM_LATE_PROBE_ACK_US="<<n::Simulator::Now().GetMicroSeconds()<<" RSU="<<owner_rsu<<" STATE="<<state<<'\n';continue;}
            probe_returned = true;
            handover_probe_returned.insert(owner_rsu);
            state = "confirmed_new";
            if (owner_rsu == rsu_id) handover_state = state;
            std::cout << "HANDOVER_ATTACH_CONFIRMED_US=" << n::Simulator::Now().GetMicroSeconds()
                      << " RSU=" << owner_rsu << '\n';
            continue;
        }
        ensure(valid_ack(ack), "UT GRA1 content invalid");
        auto id = read_u64(ack, 5);
        ensure(rsu_by_report.at(id) == owner_rsu, "gateway ACK reached another RSU terminal");
        ++ut_ack_received;
        log_bytes(backhaul_mode == "ground" ? "UT_GROUND_GRA1_RX" : "UT_SAT_GRA1_RX",
                  "ut-user", id, ack);
        ensure(rsu_lan_ack_sockets.at(owner_rsu)->SendTo(n::Create<n::Packet>(ack.data(), ack.size()), 0,
                   n::InetSocketAddress(rsu_lan_addresses.at(rsu_by_report.at(id)), ack_port)) ==
                   static_cast<int>(ack.size()),
               "UT LAN GRA1 send failed");
        log_bytes("UT_LAN_GRA1_TX", "ut-user", id, ack);
    }
}
// `rsu_ack_receive()` spracuje odpoveď doručenú z terminálu do RSU.
static void rsu_ack_receive(n::Ptr<n::Socket> sink) {
    n::Ptr<n::Packet> packet;
    while ((packet = sink->Recv())) {
        auto ack = packet_bytes(packet);
        ensure(valid_ack(ack), "RSU GRA1 content invalid");
        auto id = read_u64(ack, 5);
        ++rsu_ack_received;
        log_bytes("RSU_GRA1_RX", rsu_by_report.at(id), id, ack);
        enqueue_reverse(id);
    }
}

static void queue_log(const char* direction, std::uint64_t id, const std::string& rsu,
                      unsigned depth, const char* decision, const char* reason) {
    queue_trace << direction << ',' << id_hex(id) << ',' << rsu << ','
                << n::Simulator::Now().GetMicroSeconds() << ',' << depth << ','
                << (std::string(direction) == "forward" ? forward_queue_capacity : reverse_queue_capacity)
                << ',' << decision << ',' << reason << '\n';
}
// Ohraničený aplikačný front oddeľuje okamih, keď je hlásenie pripravené, od okamihu ponúknutia
// socketu. Kapacita a interval obsluhy sú skúmané parametre; nemýľ si úspešné vloženie do frontu s
// fyzikálnym doručením.
static bool enqueue_forward(std::uint64_t id) {
    const auto& rsu = rsu_by_report.at(id);
    const unsigned depth = forward_queue.size();
    if (depth >= forward_queue_capacity) {
        ++forward_queue_drops;
        forward_dropped_ids.insert(id);
        queue_log("forward", id, rsu, depth, "drop", "queue_full");
        log_event("dropped", rsu, id, "forward_queue_full");
        return false;
    }
    forward_queue.push_back(id);
    queue_log("forward", id, rsu, depth, "enqueue", "none");
    if (!forward_service_scheduled) {
        forward_service_scheduled = true;
        n::Simulator::Schedule(n::MicroSeconds(forward_service_us), &service_forward);
    }
    return true;
}
// `service_forward()` obslúži čakajúce hlásenia v smere RSU → brána.
static void service_forward() {
    ensure(!forward_queue.empty(), "forward service fired without queued report");
    const auto id = forward_queue.front();
    forward_queue.pop_front();
    const auto& rsu = rsu_by_report.at(id);
    const auto& report = created_reports.at(id);
    queue_log("forward", id, rsu, forward_queue.size(), "dequeue", "none");
    ++reports_offered;
    if (backhaul_mode == "local") {
        log_bytes("LOCAL_REPORT_OFFER", rsu, id, report);
        process_server_report(report);
    } else {
        log_bytes("RSU_REPORT_TX", rsu, id, report);
        ensure(report_sockets.at(rsu)->SendTo(n::Create<n::Packet>(report.data(), report.size()), 0,
                   n::InetSocketAddress(ut_lan_addresses.at(rsu), report_port)) ==
                   static_cast<int>(report.size()), "RSU UDP report send failed");
    }
    if (!forward_queue.empty())
        n::Simulator::Schedule(n::MicroSeconds(forward_service_us), &service_forward);
    else forward_service_scheduled = false;
}
// `enqueue_reverse()` vloží spätnú správu do ohraničeného frontu.
static void enqueue_reverse(std::uint64_t id) {
    const auto& rsu = rsu_by_report.at(id);
    const unsigned depth = reverse_queue.size();
    if (depth >= reverse_queue_capacity) {
        ++reverse_queue_drops;
        reverse_dropped_ids.insert(id);
        queue_log("reverse", id, rsu, depth, "drop", "queue_full");
        log_event("dropped", rsu, id, "reverse_queue_full");
        return;
    }
    reverse_queue.push_back(id);
    queue_log("reverse", id, rsu, depth, "enqueue", "none");
    if (!reverse_service_scheduled) {
        reverse_service_scheduled = true;
        n::Simulator::Schedule(n::MicroSeconds(reverse_service_us), &service_reverse);
    }
}
// `service_reverse()` obslúži čakajúce odpovede v smere brána → RSU.
static void service_reverse() {
    ensure(!reverse_queue.empty(), "reverse service fired without queued ack");
    const auto id = reverse_queue.front();
    reverse_queue.pop_front();
    const auto& rsu = rsu_by_report.at(id);
    const auto ack = make_ack(created_reports.at(id));
    const auto i2v = make_i2v1(ack);
    queue_log("reverse", id, rsu, reverse_queue.size(), "dequeue", "none");
    ensure(rsu_ocb_devices.at(rsu)->Send(n::Create<n::Packet>(i2v.data(), i2v.size()),
               car_ocb_addresses.at(station_by_report.at(id)), i2v_ethertype),
           "RSU OCB I2V1 send failed");
    log_bytes("RSU_I2V1_TX", rsu, id, i2v);
    if (!reverse_queue.empty())
        n::Simulator::Schedule(n::MicroSeconds(reverse_service_us), &service_reverse);
    else reverse_service_scheduled = false;
}

// Polia CAM vznikajú z časovanej polohy auta: WGS84, rýchlosť, smer a stav vozidla sa prevádzajú
// na jednotky ETSI. Vanetza ich kóduje do ASN.1 UPER; v raw stope možno overiť presné vyslané
// bajty.
static v::ByteBuffer make_cam(const Waypoint& w, bool low_frequency) {
    v::asn1::r2::Cam cam;
    cam->header.protocolVersion = 2;
    cam->header.messageId = 2;
    cam->header.stationId = w.station_id;
    cam->cam.generationDeltaTime = w.gdt_ms;
    auto& cp = cam->cam.camParameters;
    cp.basicContainer.stationType = Vanetza_ITS2_TrafficParticipantType_passengerCar;
    auto& p = cp.basicContainer.referencePosition;
    p.latitude = w.lat_e7; p.longitude = w.lon_e7;
    p.positionConfidenceEllipse.semiMajorAxisLength = Vanetza_ITS2_SemiAxisLength_unavailable;
    p.positionConfidenceEllipse.semiMinorAxisLength = Vanetza_ITS2_SemiAxisLength_unavailable;
    p.positionConfidenceEllipse.semiMajorAxisOrientation = Vanetza_ITS2_Wgs84AngleValue_unavailable;
    p.altitude.altitudeValue = w.alt_cm;
    p.altitude.altitudeConfidence = Vanetza_ITS2_AltitudeConfidence_unavailable;
    cp.highFrequencyContainer.present = Vanetza_ITS2_HighFrequencyContainer_PR_basicVehicleContainerHighFrequency;
    auto& vehicle = cp.highFrequencyContainer.choice.basicVehicleContainerHighFrequency;
    vehicle.heading.headingValue = w.heading_decideg;
    vehicle.heading.headingConfidence = 127;
    vehicle.speed.speedValue = w.speed_cmps;
    vehicle.speed.speedConfidence = 127;
    vehicle.driveDirection = Vanetza_ITS2_DriveDirection_forward;
    vehicle.vehicleLength.vehicleLengthValue = w.length_dm;
    vehicle.vehicleLength.vehicleLengthConfidenceIndication = 0;
    vehicle.vehicleWidth = w.width_dm;
    // Spoločný pozemný a satelitný ns-3 beh kóduje tie isté hodnoty CAM ako samostatná pozemná
    // vetva. Prijímač ich opätovne dekóduje a porovná s waypointom; zmena obsahu je tak viditeľná
    // v raw paketoch.
    vehicle.longitudinalAcceleration.value = w.accel_dmps2;
    vehicle.longitudinalAcceleration.confidence = 102;
    vehicle.curvature.curvatureValue = w.curvature_1e4;
    vehicle.curvature.curvatureConfidence = 7;
    vehicle.curvatureCalculationMode = w.curvature_1e4 == 1023 ? Vanetza_ITS2_CurvatureCalculationMode_unavailable : Vanetza_ITS2_CurvatureCalculationMode_yawRateUsed;
    vehicle.yawRate.yawRateValue = w.yaw_cdegps;
    vehicle.yawRate.yawRateConfidence = 8;
    if (low_frequency) {
        cp.lowFrequencyContainer = static_cast<Vanetza_ITS2_LowFrequencyContainer_t*>(
            std::calloc(1, sizeof(Vanetza_ITS2_LowFrequencyContainer_t)));
        ensure(cp.lowFrequencyContainer != nullptr, "CAM low-frequency allocation failed");
        cp.lowFrequencyContainer->present = Vanetza_ITS2_LowFrequencyContainer_PR_basicVehicleContainerLowFrequency;
        auto& low = cp.lowFrequencyContainer->choice.basicVehicleContainerLowFrequency;
        low.vehicleRole = Vanetza_ITS2_VehicleRole_default;
        low.exteriorLights.buf = static_cast<std::uint8_t*>(std::calloc(1, 1));
        ensure(low.exteriorLights.buf != nullptr, "CAM lights allocation failed");
        low.exteriorLights.size = 1;
        low.exteriorLights.bits_unused = 0;
        low.exteriorLights.buf[0] = w.lights;
        if (w.index >= 5) {
            const auto& prior = tracks.at(w.node_id).at(w.index - 5);
            const long dlat = prior.lat_e7 - w.lat_e7, dlon = prior.lon_e7 - w.lon_e7;
            const long dalt = prior.alt_cm - w.alt_cm;
            if (w.time_us - prior.time_us == 500000 && std::abs(dlat) < 131072 &&
                std::abs(dlon) < 131072 && std::abs(dalt) < 12800) {
                auto* point = static_cast<Vanetza_ITS2_PathPoint_t*>(std::calloc(1, sizeof(Vanetza_ITS2_PathPoint_t)));
                ensure(point != nullptr, "CAM path allocation failed");
                point->pathPosition.deltaLatitude = dlat;
                point->pathPosition.deltaLongitude = dlon;
                point->pathPosition.deltaAltitude = dalt;
                point->pathDeltaTime = static_cast<long*>(std::calloc(1, sizeof(long)));
                ensure(point->pathDeltaTime != nullptr, "CAM path time allocation failed");
                *point->pathDeltaTime = 50;
                ensure(ASN_SEQUENCE_ADD(&low.pathHistory.list, point) == 0, "CAM path append failed");
            }
        }
    }
    ensure(cam.validate(), "generated v2 CAM invalid");
    return cam.encode();
}

// `cam_matches()` porovná dekódované polia CAM s polohovou vzorkou.
static bool cam_matches(const v::asn1::r2::Cam& cam, const Waypoint& w) {
    const auto& p = cam->cam.camParameters.basicContainer.referencePosition;
    const auto& vehicle = cam->cam.camParameters.highFrequencyContainer.choice.basicVehicleContainerHighFrequency;
    return cam->header.protocolVersion == 2 && cam->header.messageId == 2 &&
        cam->header.stationId == w.station_id && cam->cam.generationDeltaTime == w.gdt_ms &&
        p.latitude == w.lat_e7 && p.longitude == w.lon_e7 && p.altitude.altitudeValue == w.alt_cm &&
        vehicle.speed.speedValue == w.speed_cmps && vehicle.heading.headingValue == w.heading_decideg &&
        vehicle.longitudinalAcceleration.value == w.accel_dmps2 &&
        vehicle.yawRate.yawRateValue == w.yaw_cdegps &&
        vehicle.curvature.curvatureValue == w.curvature_1e4 &&
        vehicle.vehicleLength.vehicleLengthValue == w.length_dm &&
        vehicle.vehicleWidth == w.width_dm &&
        p.positionConfidenceEllipse.semiMajorAxisLength == Vanetza_ITS2_SemiAxisLength_unavailable &&
        p.positionConfidenceEllipse.semiMinorAxisLength == Vanetza_ITS2_SemiAxisLength_unavailable &&
        (!cam->cam.camParameters.lowFrequencyContainer ||
         cam->cam.camParameters.lowFrequencyContainer->choice.basicVehicleContainerLowFrequency.exteriorLights.buf[0] == w.lights);
}

// Jeden objekt Station predstavuje ITS stanicu auta alebo RSU. Vlastní Vanetza GeoNetworking/BTP,
// viaže ich na ns-3 NetDevice a prijíma oznámenia z rádia. Pri čítaní sleduj poradie: poloha →
// časovač CAM/DENM → Vanetza paket → ns-3 PHY → prijímacia callback funkcia.
class Station final : public v::dcc::RequestInterface, public v::btp::IndicationInterface {
public:
    // `probe_mib()` pripraví parametre Vanetza GeoNetworking stanice.
    static v::geonet::MIB probe_mib() {
        v::geonet::MIB mib;
        mib.itsGnSecurity = false;
        mib.vanetzaDisableBeaconing = true;
        return mib;
    }
    Station(n::Ptr<n::NetDevice> device, std::string id, const std::vector<Waypoint>& track)
        : device_(device), id_(std::move(id)), track_(track), mac_(address_of(device)),
          runtime_(), mib_(probe_mib()), router_(runtime_, mib_) {
        router_.set_address(v::geonet::Address(mac_));
        router_.set_access_interface(this);
        router_.set_transport_handler(v::geonet::UpperProtocol::BTP_B, &dispatcher_);
        router_.packet_dropped = [this](v::geonet::Router::PacketDropReason reason) {
            ++gn_drops_;
            std::cerr << "GN_DROP_REASON=" << static_cast<int>(reason) << '\n';
        };
        dispatcher_.set_non_interactive_handler(v::btp::ports::CAM, this);
        if (cam_denm_mode) dispatcher_.set_non_interactive_handler(v::btp::ports::DENM, this);
        update_position(track.front(), false);
        device_->SetReceiveCallback(n::MakeCallback(&Station::receive_device, this));
    }
    // `on_state()` zaznamená čas vysielania, príjmu alebo obsadenosti rádia.
    void on_state(n::Time start, n::Time duration, WifiPhyState state) {
        const auto a = start.GetMicroSeconds(), b = a + duration.GetMicroSeconds();
        if (state == WifiPhyState::TX || state == WifiPhyState::RX || state == WifiPhyState::CCA_BUSY)
            busy_.push_back({a, b});
        phy_state_trace << id_ << ',' << a << ',' << b << ',' << static_cast<int>(state) << ','
                        << n::Simulator::Now().GetMicroSeconds() << ',' << ++phy_sequence << '\n';
    }
    // `on_drop()` zaznamená dôvod straty prijímaného pozemného rámca.
    void on_drop(n::Ptr<const n::Packet>, n::WifiPhyRxfailureReason reason) {
        ++integrated_phy_drops;
        phy_drop_trace << id_ << ',' << n::Simulator::Now().GetMicroSeconds() << ',' << reason << '\n';
    }
    // CBR je podiel poslednej sekundy, počas ktorej rádio hlásilo TX/RX/CCA_BUSY. Prekrývajúce sa
    // intervaly sa zjednotia, aby sa čas nerátal dvakrát. Táto nameraná obsadenosť ovplyvňuje DCC
    // interval, nie priamo fyzikálny dosah.
    double cbr(std::int64_t now) const {
        const auto from = now - 1000000;
        std::vector<std::pair<std::int64_t, std::int64_t>> intervals;
        for (const auto& p : busy_)
            if (p.second > from && p.first < now)
                intervals.push_back({std::max(from, p.first), std::min(now, p.second)});
        std::sort(intervals.begin(), intervals.end());
        std::int64_t total = 0, end = from;
        for (auto p : intervals)
            if (p.second > end) { total += p.second - std::max(end, p.first); end = p.second; }
        return double(total) / double(std::max<std::int64_t>(1,
            std::min<std::int64_t>(1000000, now - track_.front().time_us)));
    }
    // Pri každej vzorke sa rozhoduje, či auto vysiela nový CAM. Spúšťačom je dostatočná zmena
    // polohy/rýchlosti/smeru alebo periodický interval; DCC môže stanoviť dlhšiu minimálnu medzeru
    // pri obsadenom kanáli. Rozhodnutie aj vstupy sa zapisujú do stopy.
    void check(const Waypoint& w) {
        if (w.kind != "car" || ground_off_cars.count(id_)) return;
        const auto now = n::Simulator::Now().GetMicroSeconds();
        const double load = cbr(now);
        const int minimum = dcc_enabled ?
            (load >= dcc_high_cbr ? dcc_high_ms : (load >= dcc_low_cbr ? dcc_mid_ms : 100)) : 100;
        const auto elapsed = last_ ? now - last_->time_us : 1000000LL;
        const auto dist = last_ ? std::hypot(w.x_m-last_->x_m, w.y_m-last_->y_m) : 0.0;
        const auto speed = last_ ? std::abs(w.speed_cmps-last_->speed_cmps)/100.0 : 0.0;
        const auto angle = last_ ? std::abs(w.heading_decideg-last_->heading_decideg)/10.0 : 0.0;
        const auto heading = std::min(angle, 360.0-angle);
        const bool motion = last_ && (dist>cam_distance_m || speed>cam_speed_mps || heading>cam_heading_deg);
        const bool elapsed_ok = elapsed >= minimum*1000LL;
        const bool periodic = elapsed >= tgen_ms_*1000LL;
        const int trigger = !last_ ? 0 : (elapsed_ok && motion ? 1 : (elapsed_ok && periodic ? 2 : -1));
        const bool send = trigger >= 0;
        dcc_trace << id_ << ',' << now << ',' << ++phy_sequence << ',' << std::setprecision(9)
                  << load << ',' << minimum << ',' << tgen_ms_ << ',' << int(motion) << ','
                  << int(periodic) << ',' << trigger << ',' << int(send) << ',' << dist << ','
                  << speed << ',' << heading << '\n';
        if (send) {
            send_cam(w);
            if (trigger == 1) { tgen_ms_ = std::min<std::int64_t>(cam_tgen_max_ms,
                                      std::max<std::int64_t>(100, elapsed/1000)); periodic_count_ = 0; }
            if (trigger == 2 && ++periodic_count_ >= cam_periodic_repeat) { tgen_ms_ = cam_tgen_max_ms; periodic_count_ = 0; }
            last_ = std::make_unique<Waypoint>(w);
            last_->time_us = now;
        }
    }
    // Tu sa tá istá časová vzorka prenesie do ns-3 MobilityModel aj do Vanetza PositionFix. Výška
    // rádia je 1,5 m pre auto a 5 m pre RSU. Súčasne vzniká stopa polôh, takže možno porovnať
    // editor, replay, CAM a rádiovú geometriu.
    void update_position(const Waypoint& w, bool emit = true) {
        device_->GetNode()->GetObject<n::MobilityModel>()->SetPosition(
            n::Vector(w.x_m, w.y_m, radio_height(w)));
        v::PositionFix fix;
        fix.timestamp = runtime_.now();
        fix.latitude = (w.lat_e7 / 1e7) * v::units::degrees;
        fix.longitude = (w.lon_e7 / 1e7) * v::units::degrees;
        fix.speed = v::units::Velocity::from_value(w.speed_cmps / 100.0);
        fix.course = v::units::TrueNorth::from_value(w.heading_decideg / 10.0);
        // SUMO has an exact model position but supplies no GNSS uncertainty.
        fix.confidence.semi_major = mib_.itsGnPaiInterval;
        fix.confidence.semi_minor = mib_.itsGnPaiInterval;
        router_.update_position(fix);
        if (emit)
            mobility_trace << n::Simulator::Now().GetMicroSeconds() << ',' << id_
                           << ',' << std::fixed << std::setprecision(2) << w.x_m << ',' << w.y_m
                           << ',' << w.lat_e7 << ',' << w.lon_e7 << '\n';
    }
    // Vytvorí a cez Vanetza GeoNetworking/BTP odošle CAM ako jednoskokový SHB. ID paketu sa viaže
    // na stanicu a čas; surové CAM aj GN bajty sa ukladajú pred ponúknutím ns-3 zariadeniu.
    // Nasledujúce PHY a RX stopy rozhodnú o skutočnom výsledku.
    void send_cam(const Waypoint& w) {
        ensure(w.kind == "car" && n::Simulator::Now().GetMicroSeconds() >= w.time_us,
               "ground radio CAM sent before sampled position");
        const auto now = n::Simulator::Now().GetMicroSeconds();
        last_sample_index_ = w.index;
        const bool low_frequency = last_low_us_ < 0 || now - last_low_us_ >= cam_low_frequency_ms * 1000LL;
        current_id_ = cam_id(w, tx_sequence_++, now);
        const CamKey key{w.station_id, w.gdt_ms};
        auto cam = make_cam(w, low_frequency);
        if (low_frequency) last_low_us_ = now;
        ensure(transmitted_cam.emplace(key, std::vector<std::uint8_t>(cam.begin(), cam.end())).second,
               "ground radio CAM station/GDT reused");
        ensure(cam_event_by_key.emplace(key, current_id_).second, "ground radio CAM ID duplicated");
        identity_trace << "cam," << id_hex(current_id_) << ",," << w.station_id << ','
                       << w.gdt_ms << ',' << now << ',' << tx_sequence_-1 << '\n';
        cam_trace << "CAM_UPER_TX," << id_ << ',' << w.station_id << ',' << w.gdt_ms << ','
                  << now << ',' << hex_bytes(transmitted_cam.at(key)) << '\n';
        log_bytes("CAM_UPER_TX", id_, current_id_, cam);
        log_event("offered", id_, current_id_);
        v::btp::HeaderB btp;
        btp.destination_port = v::btp::ports::CAM;
        btp.destination_port_info = v::host_cast<std::uint16_t>(0);
        v::ByteBuffer btp_bytes;
        v::serialize_into_buffer(btp, btp_bytes);
        ensure(btp_bytes.size() == 4, "wrong BTP-B header size");
        auto packet = std::make_unique<v::DownPacket>();
        (*packet)[v::OsiLayer::Transport] = std::move(btp_bytes);
        (*packet)[v::OsiLayer::Application] = std::move(cam);
        v::geonet::ShbDataRequest request(mib_, v::aid::CA);
        request.upper_protocol = v::geonet::UpperProtocol::BTP_B;
        request.max_hop_limit = 1;
        auto confirm = router_.request(request, std::move(packet));
        ensure(confirm.accepted(), "Vanetza GN rejected ground radio CAM");
    }
    // DENM sa kóduje do UPER a posiela cez BTP port pre výstrahy. Lokálny a vzdialený pôvod
    // používajú rovnakú aplikačnú logiku, ale len úspešne prijaté bajty sa majú objaviť v cieľovej
    // RSU alebo aute.
    void emit_denm(const std::vector<std::uint8_t>& raw, std::uint64_t id,
                   unsigned radius_m, const Waypoint& area_center, bool remote) {
        current_denm_id_ = id;
        sending_denm_ = true;
        v::btp::HeaderB btp;
        btp.destination_port = v::btp::ports::DENM;
        btp.destination_port_info = v::host_cast<std::uint16_t>(0);
        v::ByteBuffer btp_bytes;
        v::serialize_into_buffer(btp, btp_bytes);
        auto packet = std::make_unique<v::DownPacket>();
        (*packet)[v::OsiLayer::Transport] = std::move(btp_bytes);
        (*packet)[v::OsiLayer::Application] = v::ByteBuffer(raw.begin(), raw.end());
        v::geonet::GbcDataRequest request(mib_, v::aid::DEN);
        request.upper_protocol = v::geonet::UpperProtocol::BTP_B;
        request.max_hop_limit = 3;
        v::geonet::Circle circle;
        circle.r = double(radius_m) * v::units::si::meters;
        request.destination.shape = circle;
        request.destination.position = v::geonet::GeodeticPosition(
            (area_center.lat_e7 / 1e7) * v::units::degrees,
            (area_center.lon_e7 / 1e7) * v::units::degrees);
        request.destination.angle = v::units::Angle::from_value(0.0);
        auto confirm = router_.request(request, std::move(packet));
        sending_denm_ = false;
        ensure(confirm.accepted(), "Vanetza GN rejected DENM GBC");
        log_bytes(remote ? "RSU_DENM_GBC_TX" : "CAR_DENM_GBC_TX", id_, id, raw);
    }
    // `send_denm()` odošle výstrahu DENM cez Vanetza a pozemné ns-3 rádio.
    void send_denm(const DenmEvent& event) {
        ensure(track_.front().kind == "car" && id_ == event.source_id,
               "DENM origin must be scheduled source car");
        auto it = std::upper_bound(track_.begin(), track_.end(), event.time_us,
            [](std::int64_t t, const Waypoint& w) { return t < w.time_us; });
        ensure(it != track_.begin(), "DENM event precedes first car position");
        const auto& w = *std::prev(it);
        const auto& previous = it - track_.begin() > 1 ? *std::prev(it, 2) : w;
        auto denm = make_denm(w, previous, event);
        const auto id = denm_id(denm);
        auto raw = denm.encode();
        ensure(decode_denm(raw) == denm, "DENM UPER roundtrip failed");
        denm_radius_by_action[{w.station_id,event.sequence}] = event.radius_m;
        log_bytes("DENM_UPER_TX", id_, id, raw);
        log_event(event.operation, id_, id, "traffic_jam_scenario_event");
        emit_denm(raw, id, event.radius_m, w, false);
        if (event.repetition_ms && event.operation != "cancel") {
            std::int64_t next_version = simulation_end_us;
            for (const auto& future : denm_events)
                if (future.source_id == event.source_id && future.sequence == event.sequence &&
                    future.time_us > event.time_us)
                    next_version = std::min(next_version, future.time_us);
            for (std::int64_t t = event.time_us + event.repetition_ms * 1000LL;
                 t < next_version && t < event.time_us +
                     std::int64_t(event.validity_s) * 1000000;
                 t += event.repetition_ms * 1000LL) {
                n::Simulator::Schedule(n::MicroSeconds(t - event.time_us),
                    [this, raw, id, radius = event.radius_m, w] {
                        log_bytes("DENM_REPEAT_TX", id_, id, raw);
                        emit_denm(raw, id, radius, w, false);
                    });
            }
        }
    }
    // `rebroadcast_denm()` znovu rozšíri relevantnú DENM v pozemnej oblasti.
    void rebroadcast_denm(const std::vector<std::uint8_t>& raw) {
        ensure(track_.front().kind == "rsu", "DENM downlink reached non-RSU");
        auto denm = decode_denm(raw);
        const auto id = denm_id(denm);
        long reference = 0;
        ensure(asn_INTEGER2long(&denm->denm.management.referenceTime, &reference) == 0,
               "remote DENM reference time invalid");
        denm_seen_[{unsigned(denm->denm.management.actionId.originatingStationId),
                    unsigned(denm->denm.management.actionId.sequenceNumber)}] = reference;
        denm->header.stationId = track_.front().station_id;
        auto regenerated = denm.encode();
        ensure(decode_denm(regenerated)->denm.management.actionId.originatingStationId ==
               denm->denm.management.actionId.originatingStationId,
               "DENM action identity changed at remote RSU");
        log_bytes("RSU_DENM_REGENERATED", id_, id, regenerated);
        emit_denm(regenerated, id,
                  denm_radius_by_action.at({unsigned(denm->denm.management.actionId.originatingStationId),
                                            unsigned(denm->denm.management.actionId.sequenceNumber)}),
                  track_.front(), true);
    }
    // `request()` prijme požiadavku Vanetza na odoslanie rámca cez ns-3 zariadenie.
    void request(const v::dcc::DataRequest& req, std::unique_ptr<v::ChunkPacket> packet) override {
        ensure(req.ether_type.host() == 0x8947, "unexpected ground radio GN L2 send");
        v::ByteBuffer wire;
        for (auto layer : v::osi_layer_range<v::OsiLayer::Network, v::OsiLayer::Application>()) {
            v::ByteBuffer bytes;
            (*packet)[layer].convert(bytes);
            wire.insert(wire.end(), bytes.begin(), bytes.end());
        }
        static constexpr std::array<std::uint8_t,4> denm_btp_port{0x07,0xd2,0,0};
        auto btp_denm = std::search(wire.begin(), wire.end(),
                                    denm_btp_port.begin(), denm_btp_port.end());
        if (cam_denm_mode && btp_denm != wire.end()) {
            std::vector<std::uint8_t> raw(std::next(btp_denm,4), wire.end());
            const auto id = denm_id(decode_denm(raw));
            log_bytes(sending_denm_ ? "GN_BTP_DENM_TX" : "GN_BTP_DENM_FORWARD_TX",
                      id_, id, wire);
            ensure(device_->Send(n::Create<n::Packet>(wire.data(), wire.size()),
                                 n::Mac48Address::GetBroadcast(), 0x8947),
                   "ns-3 DENM GBC broadcast failed");
            return;
        }
        ensure(wire.size() >= 80 && wire.size() <= 300, "GN/BTP/CAM length outside supported range");
        ++l2_tx_;
        ensure(transmitted_gn.emplace(current_id_, std::vector<std::uint8_t>(wire.begin(), wire.end())).second,
               "duplicate GN/BTP/CAM TX event");
        log_bytes("GN_BTP_CAM_TX", id_, current_id_, wire);
        const auto& w = track_.at(last_sample_index_);
        cam_trace << "GN_BTP_CAM_TX," << id_ << ',' << w.station_id << ',' << w.gdt_ms << ','
                  << n::Simulator::Now().GetMicroSeconds() << ',' << hex_bytes(wire) << '\n';
        ensure(device_->Send(n::Create<n::Packet>(wire.data(), wire.size()),
                             n::Mac48Address::GetBroadcast(), 0x8947), "ns-3 v2 broadcast Send failed");
    }
    bool receive_device(n::Ptr<n::NetDevice>, n::Ptr<const n::Packet> packet,
                        std::uint16_t protocol, const n::Address& from) {
        if ((track_.front().kind == "car" && ground_off_cars.count(id_)) ||
            (track_.front().kind == "rsu" && ground_off_rsus.count(id_))) return false;
        if (protocol == i2v_ethertype) {
            ensure(track_.front().kind == "car", "I2V1 arrived at non-car station");
            auto msg = packet_bytes(packet);
            ensure(valid_i2v1(msg), "car I2V1 content invalid");
            ensure(station_by_report.at(read_u64(msg, 5)) == track_.front().station_id,
                   "I2V1 reached the wrong origin vehicle");
            ++car_i2v_received;
            log_bytes("CAR_I2V1_RX", id_, read_u64(msg, 5), msg);
            log_event("received", id_, read_u64(msg, 5), "i2v_return");
            return true;
        }
        if (protocol != 0x8947) return false;
        ++l2_rx_;
        v::ByteBuffer bytes(packet->GetSize());
        packet->CopyData(bytes.data(), bytes.size());
        pending_wire_ = bytes;
        std::ostringstream os;
        os << n::Mac48Address::ConvertFrom(from);
        v::MacAddress sender;
        ensure(v::parse_mac_address(os.str(), sender), "invalid source MAC");
        auto up = std::make_unique<v::UpPacket>(v::CohesivePacket(std::move(bytes), v::OsiLayer::Network));
        router_.indicate(std::move(up), sender, v::cBroadcastMacAddress);
        return true;
    }
    // `indicate()` prevezme z Vanetza dekódovanú prijatú ITS správu.
    void indicate(const v::btp::DataIndication& indication, std::unique_ptr<v::UpPacket> packet) override {
        if (cam_denm_mode && indication.destination_port == v::btp::ports::DENM) {
            auto view = boost::create_byte_view(*packet, v::OsiLayer::Session, v::OsiLayer::Application);
            std::vector<std::uint8_t> raw(view.begin(), view.end());
            auto denm = decode_denm(raw);
            const auto id = denm_id(denm);
            const auto& m = denm->denm.management;
            long detected = 0, reference = 0;
            ensure(asn_INTEGER2long(&m.detectionTime, &detected) == 0 &&
                   asn_INTEGER2long(&m.referenceTime, &reference) == 0,
                   "DENM ITS timestamps cannot be read");
            const auto action = std::make_pair(unsigned(m.actionId.originatingStationId),
                                               unsigned(m.actionId.sequenceNumber));
            if (track_.front().kind == "rsu" &&
                cars_only.count(denm_origin_by_station.at(action.first))) return;
            if (track_.front().station_id == m.actionId.originatingStationId) {
                log_event("denm_rejected", id_, id, "own_action");
                return;
            }
            const long validity = m.validityDuration ? *m.validityDuration : 600;
            const auto now = its_milliseconds(n::Simulator::Now().GetMicroSeconds());
            const auto prior = denm_seen_.find(action);
            const std::string rejection = now > detected + validity * 1000 ? "expired" :
                (m.termination && prior == denm_seen_.end() ? "unknown_termination" :
                 (prior != denm_seen_.end() && reference <= prior->second ?
                    (reference == prior->second ? "duplicate" : "outdated") : ""));
            if (!rejection.empty()) {
                log_event("denm_rejected", id_, id, rejection);
                return;
            }
            denm_seen_[action] = reference;
            log_bytes("DENM_UPER_RX", id_, id, raw);
            log_event(m.termination ? "denm_cancelled" : "denm_accepted", id_, id);
            if (track_.front().kind == "rsu" && id_ == rsu_id &&
                m.actionId.originatingStationId == denm->header.stationId &&
                !satellite_off_rsus.count(id_) && denm_sat_sent[id_].insert(id).second) {
                auto socket = denm_rsu_uplink_sockets.at(id_);
                ensure(socket->SendTo(n::Create<n::Packet>(raw.data(), raw.size()), 0,
                    n::InetSocketAddress(ut_lan_addresses.at(id_), denm_uplink_port)) ==
                    static_cast<int>(raw.size()), "RSU DENM LAN send failed");
                log_bytes("RSU_DENM_LAN_TX", id_, id, raw);
            }
            return;
        }
        ensure(indication.destination_port == v::btp::ports::CAM && !indication.source_port,
               "wrong v2 BTP delivery");
        auto view = boost::create_byte_view(*packet, v::OsiLayer::Session, v::OsiLayer::Application);
        std::vector<std::uint8_t> original(view.begin(), view.end());
        v::asn1::PacketVisitor<v::asn1::r2::Cam> visitor;
        auto cam = boost::apply_visitor(visitor, *packet);
        ensure(cam && cam->validate(), "v2 CAM decode failed");
        const CamKey key{static_cast<unsigned>(cam->content()->header.stationId),
                         static_cast<long>(cam->content()->cam.generationDeltaTime)};
        auto found = sampled_cam.find(key);
        ensure(found != sampled_cam.end() && cam_matches(*cam, found->second) &&
               transmitted_cam.count(key) && transmitted_cam.at(key) == original,
               "ground radio CAM differs from source/sent bytes");
        const auto& sender = found->second;
        if (track_.front().kind == "rsu" && cars_only.count(sender.node_id)) return;
        const auto& own = track_.at(sender.index);
        ensure(own.time_us <= sender.time_us && sender.time_us - own.time_us < 500000,
               "receiver waypoint not synchronized");
        auto current = device_->GetNode()->GetObject<n::MobilityModel>()->GetPosition();
        ensure(std::abs(current.x - own.x_m) < 1e-8 && std::abs(current.y - own.y_m) < 1e-8,
               "receiver ns-3 position differs from own SUMO row");
        double distance = std::hypot(sender.x_m - own.x_m, sender.y_m - own.y_m);
        ++cam_rx_;
        if (sender.node_id == source_id) ++primary_cam_rx_;
        const auto origin_id = cam_event_by_key.at(key);
        log_bytes("GN_BTP_CAM_RX", id_, origin_id, pending_wire_);
        log_bytes("CAM_UPER_RX", id_, origin_id, original);
        rx_trace << id_ << ',' << key.first << ',' << key.second << ','
                 << n::Simulator::Now().GetMicroSeconds() << ',' << hex_bytes(original) << ','
                 << hex_bytes(pending_wire_) << '\n';
        decoded_trace << sender.index << ',' << sender.time_us << ',' << n::Simulator::Now().GetMicroSeconds()
                      << ',' << cam->content()->header.stationId << ',' << cam->content()->cam.generationDeltaTime
                      << ',' << cam->content()->cam.camParameters.basicContainer.referencePosition.latitude
                      << ',' << cam->content()->cam.camParameters.basicContainer.referencePosition.longitude
                      << ',' << cam->content()->cam.camParameters.basicContainer.referencePosition.altitude.altitudeValue
                      << ',' << cam->content()->cam.camParameters.highFrequencyContainer.choice.basicVehicleContainerHighFrequency.speed.speedValue
                      << ',' << cam->content()->cam.camParameters.highFrequencyContainer.choice.basicVehicleContainerHighFrequency.heading.headingValue
                      << ',' << id_ << ',' << own.kind << ',' << std::fixed << std::setprecision(2) << own.x_m << ',' << own.y_m
                      << ',' << std::setprecision(6) << distance << '\n';
        if (!cam_denm_mode && track_.front().kind == "rsu" && sender.kind == "car") {
            if (satellite_off_rsus.count(id_)) {
                selection_trace << id_hex(origin_id) << ',' << id_ << ','
                                << n::Simulator::Now().GetMicroSeconds() << ',' << distance
                                << ",ignored,,satellite_backhaul_disabled\n";
                return;
            }
            const auto existing = report_by_cam.find(key);
            if (existing != report_by_cam.end()) {
                selection_trace << id_hex(origin_id) << ',' << id_ << ','
                                << n::Simulator::Now().GetMicroSeconds() << ',' << distance
                                << ",duplicate," << rsu_by_report.at(existing->second)
                                << ",duplicate_after_first_decode\n";
                return;
            }
            auto id = report_id(origin_id, track_.front().station_id);
            ensure(report_by_cam.emplace(key, id).second, "duplicate selected RSU report for CAM");
            ensure(rsu_by_report.emplace(id, id_).second, "duplicate report RSU binding");
            selection_trace << id_hex(origin_id) << ',' << id_ << ','
                            << n::Simulator::Now().GetMicroSeconds() << ',' << distance
                            << ",selected," << id_ << ",first_actual_decode\n";
            ensure(cam_by_report.emplace(id, origin_id).second, "duplicate report parent");
            ensure(station_by_report.emplace(id, sender.station_id).second, "duplicate report station");
            auto report = make_report(original, id);
            ensure(created_reports.emplace(id, report).second, "duplicate RSU ICB1 event");
            identity_trace << "report," << id_hex(id) << ',' << id_hex(origin_id) << ','
                           << sender.station_id << ',' << sender.gdt_ms << ','
                           << n::Simulator::Now().GetMicroSeconds() << ",0\n";
            ++reports_created;
            log_bytes("RSU_REPORT_CREATED", id_, id, report);
            log_event("created", id_, id);
            if (enqueue_forward(id))
                log_event("queued", id_, id, "bounded_forward_queue");
        }
    }
    // `l2_tx()` vráti počítadlo odoslaných rámcov na linkovej vrstve.
    unsigned l2_tx() const { return l2_tx_; }
    // `l2_rx()` vráti počítadlo prijatých rámcov na linkovej vrstve.
    unsigned l2_rx() const { return l2_rx_; }
    // `cam_rx()` vráti počet prijatých CAM.
    unsigned cam_rx() const { return cam_rx_; }
    // `primary_cam_rx()` vráti počet CAM prijatých z primárneho zdroja.
    unsigned primary_cam_rx() const { return primary_cam_rx_; }
    // `gn_drops()` vráti počet odmietnutí vo vrstve GeoNetworking.
    unsigned gn_drops() const { return gn_drops_; }
    // `id()` vráti identitu aktuálnej stanice.
    const std::string& id() const { return id_; }
private:
    n::Ptr<n::NetDevice> device_;
    std::string id_;
    const std::vector<Waypoint>& track_;
    v::MacAddress mac_;
    SimulatorRuntime runtime_;
    v::geonet::MIB mib_;
    v::geonet::Router router_;
    v::btp::PortDispatcher dispatcher_;
    unsigned l2_tx_ = 0, l2_rx_ = 0, cam_rx_ = 0, gn_drops_ = 0;
    unsigned primary_cam_rx_ = 0;
    std::uint64_t current_id_ = 0;
    std::uint64_t current_denm_id_ = 0;
    bool sending_denm_ = false;
    std::map<std::pair<unsigned, unsigned>, long> denm_seen_;
    v::ByteBuffer pending_wire_;
    std::vector<std::pair<std::int64_t, std::int64_t>> busy_;
    std::unique_ptr<Waypoint> last_;
    std::int64_t tgen_ms_ = cam_tgen_max_ms, last_low_us_ = -1;
    unsigned periodic_count_ = 0, tx_sequence_ = 0;
    std::size_t last_sample_index_ = 0;
};

// RSU terminál prijíma natívny UDP paket určený pre satelitnú vetvu. Zaznamená prijatie a obsah;
// pokračovanie do brány musí prejsť SNS-3 kanálom a verifikáciou raw stopy.
static void denm_ut_uplink_receive(std::string owner, n::Ptr<n::Socket> sink) {
    n::Address from;
    while (auto packet = sink->RecvFrom(from)) {
        auto raw = packet_bytes(packet);
        auto denm = decode_denm(raw);
        const auto id = denm_id(denm);
        log_bytes("UT_DENM_LAN_RX", owner, id, raw);
        if (block_satellite || satellite_off_rsus.count(owner)) {
            log_event("denm_dropped", owner, id, "satellite_terminal_disabled");
            continue;
        }
        ensure(denm_ut_sat_sockets.at(owner)->SendTo(n::Create<n::Packet>(raw.data(),raw.size()), 0,
            n::InetSocketAddress(gateway_address, denm_uplink_port)) == static_cast<int>(raw.size()),
            "UT DENM satellite uplink send failed");
        log_bytes("UT_DENM_SAT_TX", owner, id, raw);
    }
}
// Brána spracuje výstrahu prijatú zo satelitného uplinku a pripraví distribúciu do cieľového
// terminálu. Rozlišuj dosiahnutie brány od prijatia cieľovým autom: ide o dve samostatné hranice
// overenia.
static void denm_gateway_receive(n::Ptr<n::Socket> sink) {
    n::Address from;
    while (auto packet = sink->RecvFrom(from)) {
        auto raw = packet_bytes(packet);
        auto denm = decode_denm(raw);
        const auto id = denm_id(denm);
        ensure(n::InetSocketAddress::IsMatchingType(from), "DENM gateway source is not IPv4");
        const auto source_ip = n::InetSocketAddress::ConvertFrom(from).GetIpv4();
        auto origin = std::find_if(rsu_sat_addresses.begin(), rsu_sat_addresses.end(),
            [source_ip](const auto& item) { return item.second == source_ip; });
        ensure(origin != rsu_sat_addresses.end(), "DENM gateway source UT is unknown");
        log_bytes("GATEWAY_DENM_RX", origin->first, id, raw);
        for (const auto& target : terminal_rsus) {
            if (target == origin->first || satellite_off_rsus.count(target) ||
                (!denm_target_rsu.empty() && target != denm_target_rsu)) continue;
            ensure(denm_gateway_socket->SendTo(n::Create<n::Packet>(raw.data(),raw.size()), 0,
                n::InetSocketAddress(rsu_sat_addresses.at(target), denm_downlink_port)) ==
                static_cast<int>(raw.size()), "gateway DENM satellite downlink send failed");
            log_bytes("GATEWAY_DENM_SAT_TX", target, id, raw);
        }
    }
}
// Cieľový terminál spracuje paket zo satelitného downlinku. Následne sa výstraha môže dostať do
// cieľovej RSU a cez jej pozemné rádio k autám; všetky prechody majú vlastnú raw stopu.
static void denm_ut_downlink_receive(std::string owner, n::Ptr<n::Socket> sink) {
    n::Address from;
    while (auto packet = sink->RecvFrom(from)) {
        auto raw = packet_bytes(packet);
        const auto id = denm_id(decode_denm(raw));
        log_bytes("UT_DENM_SAT_RX", owner, id, raw);
        ensure(denm_ut_lan_sockets.at(owner)->SendTo(n::Create<n::Packet>(raw.data(),raw.size()), 0,
            n::InetSocketAddress(rsu_lan_addresses.at(owner), denm_downlink_port)) ==
            static_cast<int>(raw.size()), "UT DENM LAN downlink send failed");
        log_bytes("UT_DENM_LAN_TX", owner, id, raw);
    }
}
// `denm_rsu_downlink_receive()` pracuje s výstrahou DENM.
static void denm_rsu_downlink_receive(std::string owner, n::Ptr<n::Socket> sink) {
    n::Address from;
    while (auto packet = sink->RecvFrom(from)) {
        auto raw = packet_bytes(packet);
        const auto id = denm_id(decode_denm(raw));
        log_bytes("RSU_DENM_LAN_RX", owner, id, raw);
        denm_stations.at(owner)->rebroadcast_denm(raw);
    }
}

// Vstup natívneho enginu. Parametre z Python runnera sa menia na uzly, rádiá, SNS-3 scenár,
// antény, časovače a stopy v jednom ns-3 Simulator::Run. Dlhý zoznam cmd.AddValue je hranica medzi
// deklarovaným scenárom a skutočným vykonávaním; pri zmene parametra over, že sa používa aj po
// cmd.Parse.
int main(int argc, char** argv) {
    try {
        std::string waypoint_file = "build/editable-v2-cam-waypoints.csv";
        std::string trace_file = "trace.csv";
        std::string delivery_file = "delivery.csv";
        std::string pcap_prefix = "editable-v2";
        std::string output_path, rsu_radio_config, car_radio_config;
        bool leo_reference = false;
        bool two_sat_isl = false;
        unsigned expected_satellites = 2;
        unsigned initial_serving_sat = 0;
        unsigned return_route_old_sat = 1, return_route_new_sat = 0;
        bool initial_return_route_update = true;
        bool no_return_route_flag = false;
        int expected_gateway_reports = -1;
        std::string utc_origin = "2026-10-22 12:45:00";
        double ut_lat = 48.1480603, ut_lon = 17.1035340, ut_alt = 0.0;
        double gw_lat = 37.8167, gw_lon = 22.6667, gw_alt = 0.0;
        double satellite_rtn_user_freq_hz = 29500000000.0, satellite_fwd_user_freq_hz = 19700000000.0,
               satellite_rtn_feeder_freq_hz = 17700000000.0;
        double satellite_ut_rx_temp_dbk = 24.6, satellite_sat_user_rx_temp_dbk = 28.4;
        double satellite_gw_rx_temp_dbk = 24.62, satellite_isl_speed_mps = 299792458.0;
        unsigned satellite_sat_queue_max_packets = 10000, satellite_control_slot_ms = 100;
        bool satellite_rtn_arq = false, satellite_fwd_acm = true, satellite_rtn_acm = true;
        std::string satellite_default_fwd_modcod = "QPSK_1_TO_2";
        std::string scenario_folder = "bp-leo-separated-beams-37741";
        std::string pattern_folder = "BpLeoSeparatedBeams37741";
        unsigned seed = 314159;
        n::CommandLine cmd(__FILE__);
        cmd.AddValue("waypoints", "strict editable-v2 FCD/WGS84 radio samples", waypoint_file);
        cmd.AddValue("source", "one ITS-G5 CAM vehicle sender", source_id);
        cmd.AddValue("rsu", "selected ITS-G5 RSU and co-located UT host", rsu_id);
        cmd.AddValue("backhaul_mode", "local, ground or satellite", backhaul_mode);
        cmd.AddValue("cam_denm_mode", "only CAM and DENM ITS application traffic", cam_denm_mode);
        cmd.AddValue("denm_events", "CSV of explicit modelled traffic events", denm_events_file);
        cmd.AddValue("denm_target_rsu", "optional remote RSU for DENM fanout", denm_target_rsu);
        cmd.AddValue("forward_queue_capacity", "bounded report queue packets", forward_queue_capacity);
        cmd.AddValue("reverse_queue_capacity", "bounded I2V return queue packets", reverse_queue_capacity);
        cmd.AddValue("forward_service_us", "report queue service interval in microseconds", forward_service_us);
        cmd.AddValue("reverse_service_us", "I2V queue service interval in microseconds", reverse_service_us);
        cmd.AddValue("scenario_id", "ground radio canonical scenario identity", scenario_identity);
        cmd.AddValue("run_id", "ground radio branch/run identity for event IDs", run_identity);
        cmd.AddValue("trace", "exact raw CAM and GN/BTP/CAM byte trace", trace_file);
        cmd.AddValue("delivery", "per-recipient observation and gate CSV", delivery_file);
        cmd.AddValue("pcap_prefix", "raw 802.11 PCAP prefix", pcap_prefix);
        cmd.AddValue("output_path", "existing directory for SNS-3 PacketTrace", output_path);
        cmd.AddValue("simulation_end_us", "optional exact end of the editor packet experiment", simulation_end_us);
        cmd.AddValue("leo_reference", "use the hypothetical LEO user/feeder reference", leo_reference);
        cmd.AddValue("two_sat_isl", "diagnostic two-satellite model ISL and byte observer", two_sat_isl);
        cmd.AddValue("expected_satellites", "number of orbit objects in the configured constellation", expected_satellites);
        cmd.AddValue("initial_serving_sat", "initial UT serving satellite index from scenario", initial_serving_sat);
        cmd.AddValue("return_route_old_sat", "initial GW satellite interface for return route", return_route_old_sat);
        cmd.AddValue("return_route_new_sat", "UT serving satellite interface for return route", return_route_new_sat);
        cmd.AddValue("initial_return_route_update", "apply explicit initial GW route reassignment", initial_return_route_update);
        // Voľba `--handover_case` sa načíta do `handover_case` a ovplyvní natívny beh.
        cmd.AddValue("handover_case", "stay, switch, no_candidate, no_beam, no_attach, no_route or attach_failed", handover_case);
        // Voľba `--handover_target_sat` sa načíta do `handover_target_sat` a ovplyvní natívny beh.
        cmd.AddValue("handover_target_sat", "target orbit object index for one-UT switch", handover_target_sat);
        // Voľba `--handover_beam` sa načíta do `handover_beam` a ovplyvní natívny beh.
        cmd.AddValue("handover_beam", "target SNS-3 diagnostic user beam", handover_beam);
        // Voľba `--handover_request_us` sa načíta do `handover_request_us` a ovplyvní natívny beh.
        cmd.AddValue("handover_request_us", "simulation microseconds of handover request", handover_request_us);
        cmd.AddValue("expected_gateway_reports", "override expected gateway count for paired no-ISL control", expected_gateway_reports);
        cmd.AddValue("utcOrigin", "UTC simulation origin matching waypoint input", utc_origin);
        cmd.AddValue("utLat", "LEO UT latitude in degrees", ut_lat);
        cmd.AddValue("utLon", "LEO UT longitude in degrees", ut_lon);
        cmd.AddValue("utAlt", "LEO UT spherical altitude in metres", ut_alt);
        cmd.AddValue("gwLat", "LEO gateway latitude in degrees", gw_lat);
        cmd.AddValue("gwLon", "LEO gateway longitude in degrees", gw_lon);
        cmd.AddValue("gwAlt", "LEO gateway spherical altitude in metres", gw_alt);
        cmd.AddValue("scenarioFolder", "LEO constellation folder", scenario_folder);
        cmd.AddValue("patternFolder", "LEO antenna pattern folder", pattern_folder);
        cmd.AddValue("satellite_ut_power_dbw", "UT PHY maximum transmit power after control attach", satellite_ut_power_dbw);
        cmd.AddValue("satellite_forward_bps", "ISL directed rate toward gateway after attach", satellite_forward_bps);
        cmd.AddValue("satellite_reverse_bps", "ISL directed rate away from gateway after attach", satellite_reverse_bps);
        cmd.AddValue("satellite_forward_queue_packets", "ISL queue capacity toward gateway", satellite_forward_queue_packets);
        cmd.AddValue("satellite_reverse_queue_packets", "ISL queue capacity away from gateway", satellite_reverse_queue_packets);
        cmd.AddValue("satellite_burst", "hold real UT ICB1 reports until release", satellite_burst);
        cmd.AddValue("satellite_burst_release_us", "UT application burst release microseconds", satellite_burst_release_us);
        cmd.AddValue("satellite_apply_us", "apply RF/ISL sensitivity after handover control", satellite_apply_us);
        cmd.AddValue("satellite_rtn_user_freq_hz", "generic DVB return user frequency", satellite_rtn_user_freq_hz);
        cmd.AddValue("satellite_fwd_user_freq_hz", "generic DVB forward user frequency", satellite_fwd_user_freq_hz);
        cmd.AddValue("satellite_rtn_feeder_freq_hz", "generic DVB return feeder frequency", satellite_rtn_feeder_freq_hz);
        cmd.AddValue("satellite_ut_rx_temp_dbk", "UT receiver temperature dBK", satellite_ut_rx_temp_dbk);
        cmd.AddValue("satellite_sat_user_rx_temp_dbk", "satellite user receiver temperature dBK", satellite_sat_user_rx_temp_dbk);
        cmd.AddValue("satellite_gw_rx_temp_dbk", "gateway receiver temperature dBK", satellite_gw_rx_temp_dbk);
        cmd.AddValue("satellite_sat_queue_max_packets", "generic satellite LLC queue packets", satellite_sat_queue_max_packets);
        cmd.AddValue("satellite_control_slot_ms", "DVB control slot interval", satellite_control_slot_ms);
        cmd.AddValue("satellite_rtn_arq", "DVB return ARQ enabled", satellite_rtn_arq);
        cmd.AddValue("satellite_fwd_acm", "DVB forward ACM enabled", satellite_fwd_acm);
        cmd.AddValue("satellite_rtn_acm", "DVB return ACM enabled", satellite_rtn_acm);
        cmd.AddValue("satellite_default_fwd_modcod", "generic DVB default forward MODCOD", satellite_default_fwd_modcod);
        cmd.AddValue("satellite_isl_speed_mps", "ISL channel propagation speed", satellite_isl_speed_mps);
        cmd.AddValue("block_satellite", "control: suppress only UT satellite send", block_satellite);
        cmd.AddValue("no_return_route", "control: do not offer GRA1 without qualified SAT1 return route", no_return_route_flag);
        cmd.AddValue("radio_mode", "friis, urban_los, urban_nlos, urban_building or urban_osm_building", radio_mode);
        cmd.AddValue("buildings", "pinned CSV for native ns-3 building channel", building_file);
        cmd.AddValue("osm_buildings", "pinned OSM polygon/height CSV", osm_building_file);
        cmd.AddValue("rsu_radio_config", "per-RSU PHY and antenna CSV", rsu_radio_config);
        cmd.AddValue("car_radio_config", "per-car PHY and antenna CSV", car_radio_config);
        // Voľba `--sat_mask_deg` sa načíta do `satellite_mask_deg` a ovplyvní natívny beh.
        cmd.AddValue("sat_mask_deg", "native SNS-3 channel elevation cutoff in degrees", satellite_mask_deg);
        cmd.AddValue("sat_terminal_config", "declared per-RSU native user-link RF conditions", satellite_terminal_config);
        cmd.AddValue("dcc", "ground model research measured-CBR CAM feedback", dcc_enabled);
        cmd.AddValue("phase_us", "ground model per-station check phase", phase_us);
        cmd.AddValue("dcc_low_cbr", "ground model research lower CBR threshold", dcc_low_cbr);
        cmd.AddValue("dcc_high_cbr", "ground model research upper CBR threshold", dcc_high_cbr);
        cmd.AddValue("dcc_mid_ms", "ground model research middle minimum CAM interval", dcc_mid_ms);
        cmd.AddValue("dcc_high_ms", "ground model research high minimum CAM interval", dcc_high_ms);
        cmd.AddValue("cam_distance_m", "CAM movement trigger distance", cam_distance_m);
        cmd.AddValue("cam_speed_mps", "CAM movement trigger speed difference", cam_speed_mps);
        cmd.AddValue("cam_heading_deg", "CAM movement trigger heading difference", cam_heading_deg);
        cmd.AddValue("cam_low_frequency_ms", "CAM low-frequency container interval", cam_low_frequency_ms);
        cmd.AddValue("cam_tgen_max_ms", "CAM maximum generation interval", cam_tgen_max_ms);
        cmd.AddValue("cam_periodic_repeat", "CAM periodic repeats before reset", cam_periodic_repeat);
        cmd.AddValue("car_antenna_height_m", "car ground antenna height", car_antenna_height_m);
        cmd.AddValue("rsu_antenna_min_height_m", "minimum RSU ground antenna height", rsu_antenna_min_height_m);
        cmd.AddValue("rsu_roof_clearance_m", "RSU antenna offset above roof", rsu_roof_clearance_m);
        cmd.AddValue("tx_power_dbm", "OCB TX power", radio_power_dbm);
        cmd.AddValue("noise_figure_db", "OCB RX noise figure", radio_noise_figure_db);
        cmd.AddValue("rate_mbps", "10 MHz OCB PHY rate: 3, 6, 12 or 24 Mbps", radio_rate_mbps);
        cmd.AddValue("channel_number", "10 MHz OCB channel: 172..184, even numbers", radio_channel_number);
        cmd.AddValue("tx_gain_dbi", "OCB TX antenna gain", radio_tx_gain_dbi);
        cmd.AddValue("rx_gain_dbi", "OCB RX antenna gain", radio_rx_gain_dbi);
        cmd.AddValue("shadowing", "3GPP V2V shadowing", radio_shadowing);
        cmd.AddValue("seed", "ns-3 RNG seed", seed);
        cmd.AddValue("run", "ns-3 RNG run index", ns3_run);
        cmd.Parse(argc, argv);
        // Natívny engine zapíše skutočne prijaté časy, ktoré potom checker porovná s uloženým
        // scenárom.
        std::cout << "NATIVE_CONTROL_TIMES HANDOVER=" << handover_request_us
                  << " APPLY=" << satellite_apply_us
                  << " RELEASE=" << satellite_burst_release_us << '\n';
        ensure(!source_id.empty() && !rsu_id.empty() && !output_path.empty() &&
               !scenario_identity.empty() && !run_identity.empty(),
               "source, rsu, ground radio identities and output_path required");
        auto valid_identity = [](const std::string& s) {
            return std::all_of(s.begin(), s.end(), [](unsigned char c) {
                return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-';
            });
        };
        ensure(valid_identity(scenario_identity) && valid_identity(run_identity),
               "ground radio identity must use lowercase ASCII, digits or hyphen");
        bool valid_utc = utc_origin.size() == 19 && utc_origin[4] == '-' &&
                         utc_origin[7] == '-' && (utc_origin[10] == 'T' || utc_origin[10] == ' ') &&
                         utc_origin[13] == ':' && utc_origin[16] == ':';
        if (valid_utc) {
            for (std::size_t i = 0; i < utc_origin.size(); ++i) {
                if (i == 4 || i == 7 || i == 10 || i == 13 || i == 16) continue;
                valid_utc = valid_utc && utc_origin[i] >= '0' && utc_origin[i] <= '9';
            }
        }
        ensure(valid_utc, "UTC origin must be YYYY-MM-DDTHH:MM:SS; orbit age is checked against the pinned OMM");
        utc_origin[10] = ' ';
        ensure(!two_sat_isl || leo_reference, "two_sat_isl requires LEO constellation");
        ensure(two_sat_isl && expected_satellites >= 1 && expected_satellites <= 40000,
               "handover requires a declared nonempty satellite constellation");
        ensure(handover_case == "stay" || handover_case == "switch" ||
               handover_case == "no_candidate" || handover_case == "no_beam" ||
               handover_case == "no_attach" || handover_case == "no_route" ||
               handover_case == "attach_failed", "invalid handover handover control");
        ensure(initial_serving_sat < expected_satellites &&
               handover_target_sat < expected_satellites && handover_beam == 30 &&
               handover_request_us >= 1000000 && handover_request_us <= 300000000,
               "invalid handover target or timing");
        ensure(std::isfinite(satellite_ut_power_dbw) && -50 <= satellite_ut_power_dbw &&
               satellite_ut_power_dbw <= 20 &&
               100 <= satellite_forward_bps && satellite_forward_bps <= 10000000000ULL &&
               100 <= satellite_reverse_bps && satellite_reverse_bps <= 10000000000ULL &&
               1 <= satellite_forward_queue_packets && satellite_forward_queue_packets <= 10000 &&
               1 <= satellite_reverse_queue_packets && satellite_reverse_queue_packets <= 10000 &&
               satellite_apply_us > handover_request_us + 1000000 &&
               satellite_burst_release_us > satellite_apply_us + 100000 &&
               satellite_burst_release_us < 300000000 &&
               std::isfinite(satellite_rtn_user_freq_hz) && 1e9 <= satellite_rtn_user_freq_hz &&
               satellite_rtn_user_freq_hz <= 5e10 &&
               std::isfinite(satellite_fwd_user_freq_hz) && 1e9 <= satellite_fwd_user_freq_hz &&
               satellite_fwd_user_freq_hz <= 5e10 &&
               std::isfinite(satellite_rtn_feeder_freq_hz) && 1e9 <= satellite_rtn_feeder_freq_hz &&
               satellite_rtn_feeder_freq_hz <= 5e10 &&
               std::isfinite(satellite_ut_rx_temp_dbk) && 0 <= satellite_ut_rx_temp_dbk &&
               satellite_ut_rx_temp_dbk <= 100 &&
               std::isfinite(satellite_sat_user_rx_temp_dbk) && 0 <= satellite_sat_user_rx_temp_dbk &&
               satellite_sat_user_rx_temp_dbk <= 100 &&
               std::isfinite(satellite_gw_rx_temp_dbk) && 0 <= satellite_gw_rx_temp_dbk &&
               satellite_gw_rx_temp_dbk <= 100 &&
               1 <= satellite_sat_queue_max_packets && satellite_sat_queue_max_packets <= 100000 &&
               10 <= satellite_control_slot_ms && satellite_control_slot_ms <= 1000 &&
               (satellite_default_fwd_modcod == "QPSK_1_TO_2" ||
                satellite_default_fwd_modcod == "QPSK_1_TO_4") &&
               std::isfinite(satellite_isl_speed_mps) && 1e8 <= satellite_isl_speed_mps &&
               satellite_isl_speed_mps <= 299792458.0,
               "satellite transport generic-DVB physics or capacity parameter outside validated bounds");
        no_return_route = no_return_route_flag;
        ensure(backhaul_mode == "local" || backhaul_mode == "ground" ||
               backhaul_mode == "satellite", "invalid backhaul backhaul mode");
        ensure(forward_queue_capacity >= 1 && forward_queue_capacity <= 1000 &&
               reverse_queue_capacity >= 1 && reverse_queue_capacity <= 1000 &&
               forward_service_us >= 1 && forward_service_us <= 1000000 &&
               reverse_service_us >= 1 && reverse_service_us <= 1000000,
               "invalid backhaul directional queue bounds/rates");
        ensure(backhaul_mode == "satellite" || (!block_satellite && !no_return_route),
               "satellite faults require satellite mode");
        ensure(radio_mode == "friis" || radio_mode == "urban_los" ||
               radio_mode == "urban_nlos" || radio_mode == "urban_building" ||
               radio_mode == "urban_osm_building", "unknown P2 radio mode");
        ensure(std::isfinite(dcc_low_cbr) && std::isfinite(dcc_high_cbr) &&
               0 <= dcc_low_cbr && dcc_low_cbr < dcc_high_cbr && dcc_high_cbr <= 1 &&
               100 <= dcc_mid_ms && dcc_mid_ms <= dcc_high_ms && dcc_high_ms <= 1000 &&
               cam_distance_m >= 0 && cam_distance_m <= 100 &&
               cam_speed_mps >= 0 && cam_speed_mps <= 20 &&
               cam_heading_deg >= 0 && cam_heading_deg <= 180 &&
               cam_low_frequency_ms >= 100 && cam_low_frequency_ms <= cam_tgen_max_ms &&
               cam_tgen_max_ms <= 1000 && cam_periodic_repeat >= 1 && cam_periodic_repeat <= 20 &&
               car_antenna_height_m >= 0.2 && car_antenna_height_m <= 10 &&
               rsu_antenna_min_height_m >= 0.2 && rsu_antenna_min_height_m <= 100 &&
               rsu_roof_clearance_m >= 0 && rsu_roof_clearance_m <= 50 &&
               phase_us <= 1000 && radio_power_dbm >= 0 && radio_power_dbm <= 33 &&
               radio_noise_figure_db >= 0 && radio_noise_figure_db <= 20 &&
               (radio_rate_mbps == 3 || radio_rate_mbps == 6 ||
                radio_rate_mbps == 12 || radio_rate_mbps == 24) &&
               radio_channel_number >= 172 && radio_channel_number <= 184 &&
               radio_channel_number % 2 == 0 &&
               std::isfinite(radio_tx_gain_dbi) && std::isfinite(radio_rx_gain_dbi) &&
               radio_tx_gain_dbi >= -20 && radio_tx_gain_dbi <= 20 &&
               radio_rx_gain_dbi >= -20 && radio_rx_gain_dbi <= 20 &&
               !(radio_mode == "friis" && radio_shadowing),
               "ground CAM/DCC/radio parameters invalid");
        building_channel = radio_mode == "urban_building" || radio_mode == "urban_osm_building";
        ensure(std::isfinite(satellite_mask_deg) && satellite_mask_deg >= -90.0 &&
               satellite_mask_deg <= 90.0, "native satellite mask invalid");
        ensure((radio_mode == "urban_building") == !building_file.empty() &&
               (radio_mode == "urban_osm_building") == !osm_building_file.empty(),
               "native building input and radio mode mismatch");
        if (radio_mode == "urban_building") load_building_boxes(building_file);
        if (radio_mode == "urban_osm_building") {
            osm_condition = n::CreateObject<groundradio::OSMBuildingCondition>();
            osm_condition->Load(osm_building_file);
        }
        runtime_origin = utc_origin;
        ensure(std::isfinite(ut_lat) && std::isfinite(ut_lon) && std::isfinite(ut_alt) &&
               ut_lat >= -90 && ut_lat <= 90 && ut_lon >= -180 && ut_lon <= 180,
               "invalid LEO UT position");
        load_waypoints(waypoint_file);
        // Aj zjednotený SNS-3 beh používa pre pozemnú RSU rovnaký per-uzlový profil. Satelitné RF
        // parametre terminálu sú oddelené od tohto OCB rádia.
        rsuradio::load(rsu_radio_config);
        // Zjednotený ns-3/SNS-3 proces používa pre autá ten istý individuálny pozemný PHY profil
        // ako pozemný engine. Satelitný terminál patrí RSU a týmto nastavením sa nemení.
        rsuradio::load_cars(car_radio_config);
        for (const auto& pair : rsuradio::profiles)
            ensure(tracks.count(pair.first) && tracks.at(pair.first).front().kind == "rsu", "RSU radio owner invalid");
        if (!rsu_radio_config.empty()) for (const auto& id : node_order)
            if (tracks.at(id).front().kind == "rsu") ensure(rsuradio::find(id) != nullptr, "RSU radio profile absent");
        for (const auto& pair : rsuradio::car_profiles)
            ensure(tracks.count(pair.first) && tracks.at(pair.first).front().kind == "car", "car radio owner invalid");
        if (!car_radio_config.empty()) for (const auto& id : node_order)
            if (tracks.at(id).front().kind == "car") ensure(rsuradio::find_car(id) != nullptr, "car radio profile absent");
        for (const auto& [id, samples] : tracks)
            if (samples.front().kind == "car")
                ensure(denm_origin_by_station.emplace(samples.front().station_id,id).second,
                       "duplicate DENM originating station identity");
        if (cam_denm_mode) {
            ensure(!denm_events_file.empty(), "CAM/DENM run needs explicit DENM event CSV");
            std::ifstream event_input(denm_events_file);
            ensure(bool(event_input), "DENM event CSV missing");
            std::string line;
            std::getline(event_input, line);
            ensure(line == "time_us,source_id,sequence,operation,validity_s,radius_m,repetition_ms",
                   "DENM event CSV header invalid");
            std::map<std::pair<std::string,unsigned>, std::int64_t> first_event;
            std::int64_t previous_time = -1;
            while (std::getline(event_input, line)) {
                if (line.empty()) continue;
                std::vector<std::string> cells;
                std::stringstream row(line);
                std::string cell;
                while (std::getline(row, cell, ',')) cells.push_back(cell);
                ensure(cells.size() == 7, "DENM event CSV row invalid");
                DenmEvent event{std::stoll(cells[0]), cells[1], unsigned(std::stoul(cells[2])), cells[3],
                    unsigned(std::stoul(cells[4])), unsigned(std::stoul(cells[5])),
                    unsigned(std::stoul(cells[6]))};
                ensure(tracks.count(event.source_id) &&
                       tracks.at(event.source_id).front().kind == "car" &&
                       event.time_us >= previous_time && event.time_us >= tracks.at(event.source_id).front().time_us &&
                       event.time_us < simulation_end_us && event.sequence <= 65535 &&
                       event.validity_s >= 1 && event.validity_s <= 86400 &&
                       event.radius_m >= 1 && event.radius_m <= 1780 &&
                       (event.repetition_ms == 0 ||
                        (event.repetition_ms >= 100 && event.repetition_ms <= 60000)) &&
                       (event.operation == "new" || event.operation == "update" ||
                        event.operation == "cancel") &&
                       (event.operation == "new" ? first_event.emplace(
                           std::make_pair(event.source_id,event.sequence),event.time_us).second :
                        first_event.count({event.source_id,event.sequence}) != 0),
                       "DENM event lifecycle or timing invalid");
                denm_events.push_back(event);
                previous_time = event.time_us;
            }
            ensure(denm_target_rsu.empty() ||
                   (tracks.count(denm_target_rsu) && denm_target_rsu != rsu_id &&
                    tracks.at(denm_target_rsu).front().kind == "rsu"),
                   "DENM remote target must be another RSU");
        }
        ground_off_cars=policy_ids("SIM_GROUND_OFF_CARS","car");
        cars_only=policy_ids("SIM_CARS_ONLY","car");
        ground_off_rsus=policy_ids("SIM_GROUND_OFF_RSUS","rsu");
        satellite_off_rsus=policy_ids("SIM_SATELLITE_OFF_RSUS","rsu");
        ensure(std::none_of(ground_off_cars.begin(),ground_off_cars.end(),
                            [](const auto& id){return cars_only.count(id);}),
               "native car policy overlaps");
        if (simulation_end_us == 0) simulation_end_us = last_cam_us + 10000000;
        ensure(simulation_end_us > last_cam_us && simulation_end_us <= last_cam_us + 10000000,
               "native editor stop must follow last CAM and precede diagnostic tail");
        ensure(satellite_burst_release_us < last_cam_us + 10000000 &&
               (!satellite_burst || satellite_burst_release_us > last_cam_us + 100000),
               "satellite transport burst release outside data/stop window");
        const std::size_t rsu_index = node_order.size() - 1;
        if (leo_reference) {
            const auto& rsu = tracks.at(rsu_id).front();
            ensure(std::abs(ut_lat * 1e7 - rsu.lat_e7) <= 1.1 &&
                   std::abs(ut_lon * 1e7 - rsu.lon_e7) <= 1.1 &&
                   std::abs(ut_alt * 100 - rsu.alt_cm) <= 1.1,
                   "LEO UT position differs from edited RSU waypoint");
        }
        // Nasledujúce výstupné súbory sú surový dôkaz behu: bajty, pohyb, dekódovanie, PHY,
        // rozhodnutia DCC, prijatia, výber RSU, fronty a satelitný RF audit. Ich otvorenie sa
        // kontroluje pred spustením. Pri analýze nespoliehaj iba na jeden súhrnný JSON.
        bytes_trace.open(trace_file);
        mobility_trace.open(pcap_prefix + "_mobility.csv");
        decoded_trace.open(pcap_prefix + "_decoded.csv");
        event_trace.open(output_path + "/events.csv");
        cam_trace.open(output_path + "/cam.csv");
        phy_state_trace.open(output_path + "/phy_state.csv");
        dcc_trace.open(output_path + "/dcc_decisions.csv");
        rx_trace.open(output_path + "/rx.csv");
        phy_drop_trace.open(output_path + "/phy_drop.csv");
        identity_trace.open(output_path + "/identity.csv");
        selection_trace.open(output_path + "/selection.csv");
        queue_trace.open(output_path + "/queue.csv");
        satellite_ip_trace.open(output_path + "/satellite-ip-trace.csv");
        if (building_channel) building_trace.open(output_path + "/building_los.csv");
        satellite_visibility_trace.open(output_path + "/satellite_visibility_drop.csv");
        ensure(bytes_trace && mobility_trace && decoded_trace && event_trace && cam_trace &&
               phy_state_trace && dcc_trace && rx_trace && phy_drop_trace && identity_trace &&
               selection_trace && queue_trace && satellite_ip_trace && satellite_visibility_trace &&
               (!building_channel || bool(building_trace)),
               "backhaul trace open failed");
        bytes_trace << "stage,node_id,event_id,time_us,bytes,raw_hex\n";
        event_trace << "event_id,stage,node_id,time_us,reason\n";
        mobility_trace << "time_us,node_id,x_m,y_m,latitude_e7,longitude_e7\n";
        decoded_trace << "index,tx_time_us,rx_time_us,station_id,generation_delta_ms,latitude_e7,longitude_e7,altitude_cm,speed_cmps,heading_decideg,rx_node_id,rx_kind,rx_x_m,rx_y_m,distance_m\n";
        cam_trace << "stage,node_id,station_id,gdt_ms,time_us,raw_hex\n";
        phy_state_trace << "node_id,start_us,end_us,state,observed_us,seq\n";
        dcc_trace << "node_id,time_us,seq,cbr_1s,dcc_min_ms,t_gen_cam_ms,motion_trigger,periodic_trigger,trigger_condition,send,distance_m,speed_delta_mps,heading_delta_deg\n";
        rx_trace << "rx_node_id,station_id,gdt_ms,time_us,cam_hex,gn_hex\n";
        phy_drop_trace << "node_id,time_us,reason\n";
        identity_trace << "kind,event_id,parent_event_id,station_id,gdt_ms,time_us,sequence\n";
        selection_trace << "cam_id,rsu_id,time_us,distance_m,decision,selected_rsu_id,reason\n";
        queue_trace << "direction,event_id,rsu_id,time_us,depth_before,capacity,decision,reason\n";
        satellite_ip_trace << "packet_uid,event_id,node_type,node_id,direction,time_us,bytes,raw_hex\n";
        if (building_channel) building_trace << "time_us,node_id,rsu_id,blocked\n";
        satellite_visibility_trace << "time_us,elevation_deg\n";
        // IP/UDP checksumy sú zapnuté, aby raw kontrola mohla rozlišovať platný a poškodený rámec.
        // Nasledujúce seed/run nastavenie určuje opakovateľnosť náhodných udalostí; až potom sa
        // vytvára topológia.
        n::GlobalValue::Bind("ChecksumEnabled", n::BooleanValue(true));
        // Seed a run index fixujú pseudonáhodné prúdy ns-3. Ich zmena môže ovplyvniť časovanie a
        // rádiové udalosti; oba patria do reprodukovateľného záznamu pokusu.
        n::RngSeedManager::SetSeed(seed);
        n::RngSeedManager::SetRun(ns3_run);
        n::Config::SetDefault("ns3::SatEnvVariables::EnableSimulationOutputOverwrite",
                              n::BooleanValue(true));
        n::Config::SetDefault("ns3::SatChannel::MinElevationAngleDeg",
                              n::DoubleValue(satellite_mask_deg));
        n::Config::SetDefault("ns3::SatHelper::PacketTraceEnabled", n::BooleanValue(true));
        if (leo_reference) {
            n::Config::SetDefault("ns3::SatConf::ForwardLinkRegenerationMode",
                n::EnumValue(n::SatEnums::REGENERATION_NETWORK));
            n::Config::SetDefault("ns3::SatConf::ReturnLinkRegenerationMode",
                n::EnumValue(n::SatEnums::REGENERATION_NETWORK));
            n::Config::SetDefault("ns3::SatHelper::SatConstellationEnabled", n::BooleanValue(true));
            n::Config::SetDefault("ns3::SatHelper::SatConstellationFolder", n::StringValue(scenario_folder));
            // Začiatok pohybu satelitov sa viaže na UTC scenára. SGP4 sa aktualizuje podľa
            // orbitálneho vstupu; náhľad glóbusu a natívny beh musia používať tú istú epochu.
            n::Config::SetDefault("ns3::SatSGP4MobilityModel::StartDateStr",
                n::StringValue(utc_origin));
            n::Config::SetDefault("ns3::SatSGP4MobilityModel::UpdatePositionEachRequest",
                n::BooleanValue(false));
            n::Config::SetDefault("ns3::SatSGP4MobilityModel::UpdatePositionPeriod",
                n::TimeValue(n::MilliSeconds(10)));
            n::Config::SetDefault("ns3::SatGwMac::SendNcrBroadcast", n::BooleanValue(false));
            n::Config::SetDefault("ns3::SatAntennaGainPatternContainer::PatternsFolder",
                n::StringValue(pattern_folder));
            n::Config::SetDefault("ns3::SatHelper::BeamNetworkAddress",
                n::Ipv4AddressValue("20.1.0.0"));
            n::Config::SetDefault("ns3::SatHelper::GwNetworkAddress",
                n::Ipv4AddressValue("10.1.0.0"));
            n::Config::SetDefault("ns3::SatHelper::UtNetworkAddress",
                n::Ipv4AddressValue("250.1.0.0"));
            n::Config::SetDefault("ns3::SatHelper::GwUsers", n::UintegerValue(1));
            n::Config::SetDefault("ns3::SatHelper::UtUsers", n::UintegerValue(1));
            n::Config::SetDefault("ns3::SatBbFrameConf::AcmEnabled", n::BooleanValue(true));
        }
        auto simulation = n::CreateObject<n::SimulationHelper>("editable-v2-ocb-sns3-dvb-gate");
        simulation->SetOutputPath(output_path);
        n::Config::SetDefault("ns3::SatConf::RtnUserLinkBaseFrequency", n::DoubleValue(satellite_rtn_user_freq_hz));
        n::Config::SetDefault("ns3::SatConf::FwdUserLinkBaseFrequency", n::DoubleValue(satellite_fwd_user_freq_hz));
        n::Config::SetDefault("ns3::SatConf::RtnFeederLinkBaseFrequency", n::DoubleValue(satellite_rtn_feeder_freq_hz));
        n::Config::SetDefault("ns3::SatUtPhy::RxTemperatureDbk", n::DoubleValue(satellite_ut_rx_temp_dbk));
        n::Config::SetDefault("ns3::SatGeoUserPhy::RxTemperatureDbk", n::DoubleValue(satellite_sat_user_rx_temp_dbk));
        // SatPhy caches EIRP during Initialize(); a later SetTxMaxPowerDbw()
        // changes only the attribute and leaves the on-air power unchanged.
        n::Config::SetDefault("ns3::SatUtPhy::TxMaxPowerDbw", n::DoubleValue(satellite_ut_power_dbw));
        n::Config::SetDefault("ns3::SatGwPhy::RxTemperatureDbk", n::DoubleValue(satellite_gw_rx_temp_dbk));
        n::Config::SetDefault("ns3::SatQueue::MaxPackets", n::UintegerValue(satellite_sat_queue_max_packets));
        n::Config::SetDefault("ns3::SatBeamScheduler::ControlSlotInterval", n::TimeValue(n::MilliSeconds(satellite_control_slot_ms)));
        n::Config::SetDefault("ns3::SatLlc::RtnLinkArqEnabled", n::BooleanValue(satellite_rtn_arq));
        n::Config::SetDefault("ns3::SatBbFrameConf::AcmEnabled", n::BooleanValue(satellite_fwd_acm));
        n::Config::SetDefault("ns3::SatWaveformConf::AcmEnabled", n::BooleanValue(satellite_rtn_acm));
        n::Config::SetDefault("ns3::SatBbFrameConf::DefaultModCod", n::StringValue(satellite_default_fwd_modcod));
        n::Config::SetDefault("ns3::PointToPointIslChannel::PropagationSpeed", n::DoubleValue(satellite_isl_speed_mps));
        n::Config::SetDefault("ns3::SatChannel::EnableRxPowerOutputTrace",
                              n::BooleanValue(true));
        std::cout << std::setprecision(15)
                  << "SATELLITE_REFERENCE_CONFIG RTN_USER_HZ=" << satellite_rtn_user_freq_hz
                  << " FWD_USER_HZ=" << satellite_fwd_user_freq_hz
                  << " RTN_FEEDER_HZ=" << satellite_rtn_feeder_freq_hz
                  << " UT_RX_DBK=" << satellite_ut_rx_temp_dbk
                  << " SAT_USER_RX_DBK=" << satellite_sat_user_rx_temp_dbk
                  << " GW_RX_DBK=" << satellite_gw_rx_temp_dbk
                  << " SAT_QUEUE_P=" << satellite_sat_queue_max_packets
                  << " CONTROL_SLOT_MS=" << satellite_control_slot_ms
                  << " RTN_ARQ=" << satellite_rtn_arq
                  << " FWD_ACM=" << satellite_fwd_acm
                  << " RTN_ACM=" << satellite_rtn_acm
                  << " FWD_MODCOD=" << satellite_default_fwd_modcod
                  << " ISL_SPEED_MPS=" << satellite_isl_speed_mps << '\n';
        // Natívny simulátor sa zastaví presne na konci zvoleného intervalu. Aplikačné udalosti
        // začínajú v t = 0 až po synchrónnom zostavení celej topológie a socketov.
        simulation->SetSimulationTime(n::MicroSeconds(simulation_end_us));
        if (leo_reference) simulation->SetBeamSet(two_sat_isl ? std::set<unsigned>{30} :
                                                                std::set<unsigned>{30, 43});
        if (leo_reference) simulation->SetUserCountPerUt(1);
        // SNS-3 tu vytvára skutočné uzly konštelácie, terminály, bránu, lúče a satelitné
        // zariadenia. To je paketový model s generickým DVB modemom; geometrická predpoveď z
        // Pythonu sama pakety neprenáša.
        auto satellite = leo_reference ? simulation->CreateSatScenario() :
                                         simulation->CreateSatScenario(n::SatHelper::SIMPLE);
        if (leo_reference) {
            auto patterns = satellite->GetAntennaGainPatterns();
            ensure(patterns->GetBestBeamId(initial_serving_sat, n::GeoCoordinate(ut_lat, ut_lon, ut_alt), false) == 30,
                   "LEO user beam not 30");
            const unsigned feeder_beam = two_sat_isl ? 30 : 43;
            if (!two_sat_isl)
                ensure(patterns->GetBestBeamId(return_route_new_sat, n::GeoCoordinate(gw_lat, gw_lon, gw_alt), true) == 43,
                       "LEO feeder beam not 43");
            std::cout << "LEO_REFERENCE_USER_BEAM=30 FEEDER_BEAM=" << feeder_beam << '\n';
            for (unsigned index = 0; index < cam_count; ++index) {
                n::Simulator::Schedule(n::MicroSeconds(tracks.at(source_id)[index].time_us),
                                       [patterns, index, ut_lat, ut_lon, ut_alt, gw_lat, gw_lon, gw_alt, feeder_beam, initial_serving_sat, return_route_new_sat] {
                    auto mobility = patterns->GetAntennaMobility(initial_serving_sat);
                    n::GeoCoordinate ut_pos(ut_lat, ut_lon, ut_alt);
                    n::GeoCoordinate gw_pos(gw_lat, gw_lon, gw_alt);
                    const double ut_gain = patterns->GetAntennaGainPattern(30)->GetAntennaGain_lin(ut_pos, mobility);
                    const double gw_gain = patterns->GetAntennaGainPattern(feeder_beam)->GetAntennaGain_lin(gw_pos, mobility);
                    ensure(std::isfinite(ut_gain) && ut_gain > 0 &&
                           std::isfinite(gw_gain) && gw_gain > 0, "LEO beam gain invalid");
                    ensure(patterns->GetBestBeamId(initial_serving_sat, ut_pos, false) == 30 &&
                           patterns->GetBestBeamId(return_route_new_sat, gw_pos, true) == feeder_beam,
                           "LEO beam selection changed during pilot");
                    std::cout << std::setprecision(12) << "LEO_SAMPLE=" << index << ','
                              << n::Simulator::Now().GetMicroSeconds() << ','
                              << mobility->GetGeoPosition().GetAltitude() << ','
                              << n::SatUtils::LinearToDb(ut_gain) << ','
                              << n::SatUtils::LinearToDb(gw_gain) << '\n';
                });
            }
        }
        auto ut_users = satellite->GetUtUsers();
        auto gateway_users = satellite->GetGwUsers();
        ensure(ut_users.GetN() && gateway_users.GetN(), "SNS-3 UT or gateway user absent");
        // Vytvorí usporiadaný zoznam RSU, ktoré majú satelitné terminály. Poradie musí sedieť s
        // poradím UT uzlov SNS-3; následná kontrola zabráni tomu, aby chýbajúci terminál potichu
        // odpadol.
        terminal_rsus.push_back(rsu_id);
        for (const auto& id : active_rsus) if (id != rsu_id) terminal_rsus.push_back(id);
        ensure(ut_users.GetN() >= terminal_rsus.size(), "RSU terminal population incomplete");
        if (!satellite_terminal_config.empty()) {
            // Pre každý aktívny terminál sa zaregistruje montážny profil, poloha a aktuálne
            // slúžiaci satelit. Callback je vložený priamo do SatChannel; odmietnutie linku sa tak
            // udeje pri natívnom paketovom pokuse.
            satellite_condition = std::make_unique<satelliteradio::Condition>(satellite_terminal_config,
                output_path + "/satellite_rf.csv", osm_condition);
            for (unsigned terminal = 0; terminal < terminal_rsus.size(); ++terminal) {
                const auto& owner = terminal_rsus.at(terminal);
                const auto& site = tracks.at(owner).front();
                satellite_condition->Register(owner,
                    satellite->UtNodes().Get(terminal)->GetObject<n::SatMobilityModel>(),
                    site.lat_e7 / 1e7, site.lon_e7 / 1e7, site.x_m, site.y_m, radio_height(site),
                    initial_serving_sat);
            }
            for (unsigned sat = 0; sat < satellite->GeoSatNodes().GetN(); ++sat)
                satellite_condition->RegisterSatellite(sat,
                    satellite->GeoSatNodes().Get(sat)->GetObject<n::SatMobilityModel>());
            ensure(satellite_condition->Registered() == terminal_rsus.size(),
                   "native satellite condition does not cover every RSU terminal");
            n::SatChannel::SetGroundLinkGate([](n::Ptr<n::MobilityModel> ground,
                n::Ptr<n::MobilityModel> orbital, n::SatEnums::ChannelType_t channel,
                double carrier_hz) {
                return satellite_condition->Accept(ground, orbital, channel, carrier_hz);
            });
            std::cout << "SIM_NATIVE_RF_TERMINALS=" << terminal_rsus.size() << '\n';
        }
        bool model_has_isl = false;
        std::vector<n::Ptr<n::SatNetDevice>> gateway_sat_devices(expected_satellites);
        if (two_sat_isl) {
            const auto sats = satellite->GeoSatNodes();
            ensure(sats.GetN() == expected_satellites,
                   "created satellite count differs from declared orbit objects");
            std::vector<unsigned> device_count(sats.GetN(), 0);
            std::vector<n::Ptr<n::PointToPointIslNetDevice>> isl_devices;
            for (unsigned sat = 0; sat < sats.GetN(); ++sat) {
                sat_node_index.emplace(sats.Get(sat)->GetId(), sat);
                for (unsigned i = 0; i < sats.Get(sat)->GetNDevices(); ++i) {
                    auto device = n::DynamicCast<n::PointToPointIslNetDevice>(sats.Get(sat)->GetDevice(i));
                    if (device) {
                        device->SetPromiscReceiveCallback(n::MakeCallback(&on_isl_report));
                        isl_devices.push_back(device);
                        ++device_count[sat];
                    }
                }
            }
            const unsigned total_isl_devices = std::accumulate(device_count.begin(), device_count.end(), 0U);
            ensure(total_isl_devices % 2 == 0, "unexpected asymmetric ISL device count");
            std::vector<std::set<unsigned>> adjacency(sats.GetN());
            for (auto device : isl_devices) {
                const unsigned a = sat_node_index.at(device->GetNode()->GetId());
                const unsigned b = sat_node_index.at(device->GetDestinationNode()->GetId());
                adjacency[a].insert(b);
            }
            std::vector<int> feeder_hops(sats.GetN(), -1);
            std::deque<unsigned> pending_sats{return_route_new_sat};
            feeder_hops[return_route_new_sat] = 0;
            while (!pending_sats.empty()) {
                unsigned here = pending_sats.front(); pending_sats.pop_front();
                for (auto neighbor : adjacency[here]) if (feeder_hops[neighbor] < 0) {
                    feeder_hops[neighbor] = feeder_hops[here] + 1;
                    pending_sats.push_back(neighbor);
                }
            }
            ensure(std::all_of(feeder_hops.begin(), feeder_hops.end(),
                               [](int x) { return x >= 0; }),
                   "satellite transport ISL pool not connected to feeder");
            for (auto device : isl_devices) {
                const unsigned a = sat_node_index.at(device->GetNode()->GetId());
                const unsigned b = sat_node_index.at(device->GetDestinationNode()->GetId());
                ensure(feeder_hops[a] != feeder_hops[b],
                       "satellite transport lateral ISL edge lacks directional capacity classification");
                const bool forward = feeder_hops[a] > feeder_hops[b];
                const std::string direction = forward ? "forward" : "reverse";
                const std::string edge = "sat" + std::to_string(a) + "-to-sat" + std::to_string(b);
                auto queue = device->GetQueue();
                ensure(queue &&
                       queue->TraceConnectWithoutContext("Enqueue", n::MakeBoundCallback(
                           &satellite_queue_packet, std::string("ENQUEUE"), direction, edge)) &&
                       queue->TraceConnectWithoutContext("Dequeue", n::MakeBoundCallback(
                           &satellite_queue_packet, std::string("DEQUEUE"), direction, edge)) &&
                       queue->TraceConnectWithoutContext("DropBeforeEnqueue", n::MakeBoundCallback(
                           &satellite_queue_packet, std::string("DROP"), direction, edge)),
                       "satellite transport native ISL queue trace unavailable");
                const auto rate = forward ? satellite_forward_bps : satellite_reverse_bps;
                const auto capacity = forward ? satellite_forward_queue_packets : satellite_reverse_queue_packets;
                n::Simulator::Schedule(n::MicroSeconds(satellite_apply_us),
                    [device, queue, rate, capacity, edge, direction] {
                        device->SetDataRate(n::DataRate(rate));
                        queue->SetMaxSize(n::QueueSize(std::to_string(capacity) + "p"));
                        std::cout << "SATELLITE_ISL_CONFIG=" << edge
                                  << " DIRECTION=" << direction
                                  << " RATE_BPS=" << rate
                                  << " QUEUE_PACKETS=" << capacity
                                  << " TIME_US=" << n::Simulator::Now().GetMicroSeconds() << '\n';
                    });
            }
            model_has_isl = total_isl_devices > 0 || sats.GetN() == 1;
            std::cout << "SATELLITE_COUNT=" << sats.GetN()
                      << " ISL_RX_DEVICE_COUNT=" << total_isl_devices << '\n';
            for (unsigned sat = 0; sat < sats.GetN(); ++sat) {
                auto geo = n::DynamicCast<n::SatGeoNetDevice>(sats.Get(sat)->GetDevice(0));
                ensure(geo, "handover satellite geo device absent");
                std::cout << "HANDOVER_INITIAL_ATTACH_SAT=" << sat
                          << " GW=" << geo->GetGwConnected().size()
                          << " UT=" << geo->GetUtConnected().size() << '\n';
            }
            auto gw_node = satellite->GwNodes().Get(0);
            for (unsigned i = 0; i < gw_node->GetNDevices(); ++i) {
                auto candidate = n::DynamicCast<n::SatNetDevice>(gw_node->GetDevice(i));
                if (candidate) {
                    const auto sat_id = candidate->GetMac()->GetSatId();
                    ensure(sat_id < sats.GetN() && !gateway_sat_devices[sat_id],
                           "ambiguous GW satellite device");
                    gateway_sat_devices[sat_id] = candidate;
                }
            }
            if (!no_return_route && model_has_isl && sats.GetN() > 1 &&
                initial_return_route_update) {
                ensure(return_route_old_sat < sats.GetN() &&
                       return_route_new_sat < sats.GetN() &&
                       gateway_sat_devices[return_route_old_sat] &&
                       gateway_sat_devices[return_route_new_sat],
                       "qualified return interfaces absent");
                for (unsigned terminal = 0; terminal < active_rsus.size(); ++terminal) {
                    auto ut_node = satellite->UtNodes().Get(terminal);
                    n::Ptr<n::SatNetDevice> ut_radio;
                    for (unsigned i = 0; i < ut_node->GetNDevices(); ++i) {
                        auto candidate = n::DynamicCast<n::SatNetDevice>(ut_node->GetDevice(i));
                        if (candidate) {
                            ensure(!ut_radio, "ambiguous RSU UT satellite device");
                            ut_radio = candidate;
                        }
                    }
                    ensure(ut_radio, "RSU satellite radio absent");
                    satellite->GetUserHelper()->UpdateGwRoutes(
                        ut_radio->GetAddress(), gateway_sat_devices[return_route_old_sat]->GetAddress(),
                        gateway_sat_devices[return_route_new_sat]->GetAddress());
                    std::cout << "SIM_RSU_RETURN_ROUTE=" << terminal_rsus.at(terminal)
                              << " OLD=" << return_route_old_sat << " NEW=" << return_route_new_sat << '\n';
                }
                std::cout << "GW_UT_RETURN_ROUTE=" << return_route_old_sat << "_TO_"
                          << return_route_new_sat << '\n';
            }
        }
        auto ut = ut_users.Get(0);
        auto gateway = gateway_users.Get(0);
        {
            auto ut_node = satellite->UtNodes().Get(0);
            n::Ptr<n::SatUtPhy> phy;
            for (unsigned i = 0; i < ut_node->GetNDevices(); ++i)
                if (auto radio = n::DynamicCast<n::SatNetDevice>(ut_node->GetDevice(i))) {
                    ensure(!phy, "satellite transport requires one UT satellite radio");
                    phy = n::DynamicCast<n::SatUtPhy>(radio->GetPhy());
                }
            ensure(phy != nullptr, "satellite transport UT PHY absent");
            ensure(std::abs(phy->GetTxMaxPowerDbw() - satellite_ut_power_dbw) < 1e-9,
                   "satellite transport UT PHY creation did not apply declared transmit power");
            std::cout << "SATELLITE_UT_POWER_DBW=" << phy->GetTxMaxPowerDbw()
                      << " TIME_US=0\n";
        }
        gateway_address = satellite->GetUserAddress(gateway);
        ut_sat_address = satellite->GetUserAddress(ut);
        for (unsigned i = 0; i < terminal_rsus.size(); ++i) {
            auto owner = terminal_rsus[i];
            auto owner_ut = ut_users.Get(i);
            auto address = satellite->GetUserAddress(owner_ut);
            ensure(rsu_sat_addresses.emplace(owner, address).second, "duplicate RSU terminal owner");
            auto mobility = satellite->UtNodes().Get(i)->GetObject<n::SatMobilityModel>();
            ensure(mobility, "RSU terminal mobility missing");
            std::cout << "SIM_RSU_TERMINAL=" << owner << " UT_NODE=" << satellite->UtNodes().Get(i)->GetId()
                      << " USER_NODE=" << owner_ut->GetId() << " IP=" << address
                      << " LAT=" << std::setprecision(12) << mobility->GetGeoPosition().GetLatitude()
                      << " LON=" << mobility->GetGeoPosition().GetLongitude() << '\n';
        }
        n::NodeContainer nodes;
        nodes.Create(node_order.size());
        n::NodeContainer radio_nodes;
        for (unsigned i = 0; i < node_order.size(); ++i) radio_nodes.Add(nodes.Get(i));
        // Pozemné uzly začnú v počiatočných lokálnych polohách. Neskoršie časované waypointy ich
        // posúvajú a aktualizujú Vanetza; pevná RSU ostáva na zadanom bode.
        n::MobilityHelper mobility;
        auto positions = n::CreateObject<n::ListPositionAllocator>();
        for (const auto& id : node_order)
            positions->Add(n::Vector(tracks.at(id).front().x_m, tracks.at(id).front().y_m,
                                     radio_height(tracks.at(id).front())));
        mobility.SetPositionAllocator(positions);
        mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
        mobility.Install(radio_nodes);
        if (radio_mode == "urban_building") {
            for (const auto& box : building_boxes) {
                auto obstacle = n::CreateObject<n::Building>();
                obstacle->SetBoundaries(n::Box(box.xmin, box.xmax, box.ymin,
                                               box.ymax, box.zmin, box.zmax));
            }
            n::BuildingsHelper::Install(radio_nodes);
            std::cout << "SIM_NATIVE_BUILDING_BOXES=" << building_boxes.size() << '\n';
        }
        const std::string rate = "OfdmRate" + std::to_string(radio_rate_mbps) + "MbpsBW10MHz";
        const double frequency_hz = (5000 + 5 * radio_channel_number) * 1e6;
        n::Config::SetDefault("ns3::WifiRemoteStationManager::NonUnicastMode", n::StringValue(rate));
        n::Wifi80211pHelper wifi = n::Wifi80211pHelper::Default();
        wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager", "DataMode", n::StringValue(rate),
                                     "ControlMode", n::StringValue(rate));
        n::YansWifiPhyHelper phy;
        // Voľba modelu pozemného útlmu: Friis ako voľné pole alebo mestský V2V model s LOS/NLOS
        // podmienkou. Pri OSM budovách sa podmienka získava z ich geometrie. Výber modelu zásadne
        // ovplyvní dosah a preto patrí do záznamu scenára.
        if (radio_mode == "friis") {
            n::YansWifiChannelHelper channel;
            channel.SetPropagationDelay("ns3::ConstantSpeedPropagationDelayModel");
            channel.AddPropagationLoss("ns3::FriisPropagationLossModel", "Frequency", n::DoubleValue(frequency_hz));
            phy.SetChannel(channel.Create());
        } else {
            n::Ptr<n::ChannelConditionModel> condition;
            if (radio_mode == "urban_los")
                condition = n::CreateObject<n::AlwaysLosChannelConditionModel>();
            else if (radio_mode == "urban_nlos")
                condition = n::CreateObject<n::NeverLosChannelConditionModel>();
            else if (radio_mode == "urban_osm_building")
                condition = osm_condition;
            else
                condition = n::CreateObject<n::ThreeGppV2vUrbanChannelConditionModel>();
            condition->AssignStreams(5);
            auto loss = n::CreateObject<n::ThreeGppV2vUrbanPropagationLossModel>();
            loss->SetAttribute("Frequency", n::DoubleValue(frequency_hz));
            loss->SetAttribute("ShadowingEnabled", n::BooleanValue(radio_shadowing));
            loss->SetAttribute("BuildingPenetrationLossesEnabled", n::BooleanValue(false));
            loss->SetAttribute("ChannelConditionModel", n::PointerValue(condition));
            loss->AssignStreams(10);
            auto channel = n::CreateObject<n::YansWifiChannel>();
            channel->SetPropagationLossModel(loss);
            channel->SetPropagationDelayModel(n::CreateObject<n::ConstantSpeedPropagationDelayModel>());
            phy.SetChannel(channel);
            std::cout << "P2_RADIO_MODE=" << radio_mode << " SHADOWING=" << radio_shadowing
                      << " FREQUENCY_HZ=" << std::fixed << std::setprecision(0) << frequency_hz
                      << std::defaultfloat << '\n';
        }
        phy.Set("ChannelSettings", n::StringValue("{" + std::to_string(radio_channel_number) + ", 10, BAND_5GHZ, 0}"));
        phy.Set("TxPowerStart", n::DoubleValue(radio_power_dbm));
        phy.Set("TxPowerEnd", n::DoubleValue(radio_power_dbm));
        phy.Set("TxGain", n::DoubleValue(radio_tx_gain_dbi));
        phy.Set("RxGain", n::DoubleValue(radio_rx_gain_dbi));
        phy.Set("RxNoiseFigure", n::DoubleValue(radio_noise_figure_db));
        std::cout << "OCB_CONFIG RATE_MBPS=" << radio_rate_mbps
                  << " CHANNEL=" << radio_channel_number
                  << " FREQUENCY_HZ=" << std::fixed << std::setprecision(0) << frequency_hz << std::defaultfloat
                  << " TX_GAIN_DBI=" << radio_tx_gain_dbi
                  << " RX_GAIN_DBI=" << radio_rx_gain_dbi
                  << " SHADOWING=" << radio_shadowing << '\n';
        phy.SetPcapDataLinkType(n::WifiPhyHelper::DLT_IEEE802_11);
        n::QosWaveMacHelper mac = n::QosWaveMacHelper::Default();
        // Každý pozemný uzol dostane ns-3 Wi-Fi/OCB zariadenie. Nasledujúce kontroly potvrdzujú 10
        // MHz kanál a režim OCB; PCAP a PHY drop callbacky zachytávajú rámce a straty.
        auto devices = wifi.Install(phy, mac, radio_nodes);
        for (std::size_t i = 0; i < node_order.size(); ++i) {
            auto wifi_dev = n::DynamicCast<n::WifiNetDevice>(devices.Get(i));
            ensure(wifi_dev && n::DynamicCast<n::OcbWifiMac>(wifi_dev->GetMac()),
                   "radio MAC is not OCB");
            const bool car = tracks.at(node_order[i]).front().kind == "car";
            if (const auto* profile = car ? rsuradio::find_car(node_order[i]) : rsuradio::find(node_order[i])) {
                wifi_dev->GetPhy()->SetAttribute("TxPowerStart", n::DoubleValue(profile->power));
                wifi_dev->GetPhy()->SetAttribute("TxPowerEnd", n::DoubleValue(profile->power));
                wifi_dev->GetPhy()->SetAttribute("RxNoiseFigure", n::DoubleValue(profile->noise));
                wifi_dev->GetPhy()->SetAttribute("TxGain", n::DoubleValue(profile->tx_gain));
                wifi_dev->GetPhy()->SetAttribute("RxGain", n::DoubleValue(profile->rx_gain));
                std::cout << std::setprecision(12) << (car ? "CAR_RADIO_PROFILE ID=" : "RSU_RADIO_PROFILE ID=") << node_order[i] << " TX=" << profile->power
                          << " NOISE=" << profile->noise << " TX_GAIN=" << profile->tx_gain
                          << " RX_GAIN=" << profile->rx_gain << " HEIGHT=" << profile->height << '\n' << std::setprecision(6);
            }
            ensure(wifi_dev->GetPhy()->GetChannelNumber() == radio_channel_number &&
                   wifi_dev->GetPhy()->GetChannelWidth() == 10 &&
                   wifi_dev->GetPhy()->GetFrequency() == 5000 + 5 * radio_channel_number,
                   "wrong v2 OCB channel");
        }
        phy.EnablePcap(pcap_prefix, devices);
        for (std::size_t i = 0; i < devices.GetN(); ++i) {
            auto wifi_phy = n::DynamicCast<n::WifiNetDevice>(devices.Get(i))->GetPhy();
            ensure(wifi_phy->TraceConnectWithoutContext("PhyRxDrop",
                       n::MakeBoundCallback(&on_wifi_phy_drop, node_order[i])),
                   "P2 Wi-Fi PHY drop callback absent");
        }
        for (std::size_t i = 0; i < node_order.size(); ++i)
            if (tracks.at(node_order[i]).front().kind == "car")
                car_ocb_addresses.emplace(tracks.at(node_order[i]).front().station_id,
                                          devices.Get(i)->GetAddress());
        for (std::size_t i = 0; i < node_order.size(); ++i)
            if (tracks.at(node_order[i]).front().kind == "rsu")
                rsu_ocb_devices.emplace(node_order[i], devices.Get(i));
        ensure(rsu_ocb_devices.size() == active_rsus.size(), "backhaul RSU OCB mapping incomplete");
        n::InternetStackHelper internet;
        for (const auto& id : active_rsus) {
            const auto index = std::find(node_order.begin(), node_order.end(), id) - node_order.begin();
            internet.Install(nodes.Get(index));
        }
        // Virtuálny drôt prepája každú RSU s jej vlastným satelitným terminálom. Jeho rýchlosť a
        // oneskorenie sú explicitné modelové parametre; samotná RSU nemá byť magicky priamo na
        // satelitnom rádiu.
        n::PointToPointHelper lan;
        lan.SetDeviceAttribute("DataRate", n::StringValue("100Mbps"));
        lan.SetChannelAttribute("Delay", n::TimeValue(n::MicroSeconds(100)));
        n::Ipv4AddressHelper addresses;
        addresses.SetBase("10.90.0.0", "255.255.255.0");
        for (const auto& id : active_rsus) {
            const auto index = std::find(node_order.begin(), node_order.end(), id) - node_order.begin();
            auto link = lan.Install(nodes.Get(index), ut_users.Get(std::find(terminal_rsus.begin(), terminal_rsus.end(), id) - terminal_rsus.begin()));
            auto ips = addresses.Assign(link);
            rsu_lan_addresses.emplace(id, ips.GetAddress(0));
            ut_lan_addresses.emplace(id, ips.GetAddress(1));
            lan.EnablePcap(pcap_prefix + "-lan-" + id, link);
            for (unsigned i = 0; i < link.GetN(); ++i)
                for (const auto& trace_name : {"MacTxDrop", "PhyTxDrop", "PhyRxDrop"})
                    ensure(link.Get(i)->TraceConnectWithoutContext(trace_name,
                               n::MakeBoundCallback(&on_lan_drop,
                                   id + "_LAN_DEVICE" + std::to_string(i) + '_' + trace_name)),
                           "backhaul LAN drop callback absent");
            report_sockets.emplace(id, bind_udp(nodes.Get(index), ips.GetAddress(0), 0));
            if (cam_denm_mode) {
                denm_rsu_uplink_sockets.emplace(id, bind_udp(nodes.Get(index), ips.GetAddress(0), 0));
                auto downlink = bind_udp(nodes.Get(index), ips.GetAddress(0), denm_downlink_port);
                downlink->SetRecvCallback(n::MakeBoundCallback(&denm_rsu_downlink_receive, id));
            }
            auto rsu_ack_sink = bind_udp(nodes.Get(index), ips.GetAddress(0), ack_port);
            rsu_ack_sink->SetRecvCallback(n::MakeCallback(&rsu_ack_receive));
            addresses.NewNetwork();
        }
        if (backhaul_mode == "ground") {
            n::PointToPointHelper bypass;
            bypass.SetDeviceAttribute("DataRate", n::StringValue("100Mbps"));
            bypass.SetChannelAttribute("Delay", n::TimeValue(n::MicroSeconds(100)));
            auto link = bypass.Install(ut, gateway);
            n::Ipv4AddressHelper bypass_ips;
            bypass_ips.SetBase("10.92.0.0", "255.255.255.0");
            auto ips = bypass_ips.Assign(link);
            ut_ground_address = ips.GetAddress(0);
            gateway_ground_address = ips.GetAddress(1);
            bypass.EnablePcap(pcap_prefix + "-ground", link);
            ground_socket = bind_udp(ut, ut_ground_address, 0);
        }
        for (unsigned i = 0; i < terminal_rsus.size(); ++i) {
            const auto& owner = terminal_rsus[i];
            auto user = ut_users.Get(i);
            auto sink = bind_udp(user, n::Ipv4Address::GetAny(), report_port);
            sink->SetRecvCallback(n::MakeBoundCallback(&ut_receive, owner));
            rsu_satellite_sockets.emplace(owner, bind_udp(user, n::Ipv4Address::GetAny(), 0));
            auto ack_sink = bind_udp(user, n::Ipv4Address::GetAny(), ack_port);
            ack_sink->SetRecvCallback(n::MakeBoundCallback(&ut_ack_receive, owner));
            rsu_lan_ack_sockets.emplace(owner, bind_udp(user, n::Ipv4Address::GetAny(), 0));
            if (cam_denm_mode) {
                auto uplink = bind_udp(user, n::Ipv4Address::GetAny(), denm_uplink_port);
                uplink->SetRecvCallback(n::MakeBoundCallback(&denm_ut_uplink_receive, owner));
                denm_ut_sat_sockets.emplace(owner, bind_udp(user, n::Ipv4Address::GetAny(), 0));
                auto downlink = bind_udp(user, n::Ipv4Address::GetAny(), denm_downlink_port);
                downlink->SetRecvCallback(n::MakeBoundCallback(&denm_ut_downlink_receive, owner));
                denm_ut_lan_sockets.emplace(owner, bind_udp(user, n::Ipv4Address::GetAny(), 0));
            }
        }
        satellite_socket = rsu_satellite_sockets.at(rsu_id);
        auto server_sink = bind_udp(gateway,
            backhaul_mode == "ground" ? gateway_ground_address : gateway_address, report_port);
        server_sink->SetRecvCallback(n::MakeCallback(&server_receive));
        gateway_ack_socket = bind_udp(gateway, n::Ipv4Address::GetAny(), 0);
        if (cam_denm_mode) {
            auto denm_sink = bind_udp(gateway, gateway_address, denm_uplink_port);
            denm_sink->SetRecvCallback(n::MakeCallback(&denm_gateway_receive));
            denm_gateway_socket = bind_udp(gateway, n::Ipv4Address::GetAny(), 0);
        }
        // Pri naplánovanom prepnutí sa pre každý RSU terminál vytvorí samostatný čas požiadavky a
        // stav. Kód kontroluje cieľový lúč, pripojenie a trasu. Nejde o úplnú autentickú politiku
        // operátora ani o ľubovoľný počet neplánovaných handoverov.
        if (handover_case != "stay") {
            ensure(backhaul_mode == "satellite" && expected_satellites >= 2 &&
                   handover_target_sat != initial_serving_sat &&
                   gateway_sat_devices[return_route_new_sat] &&
                   gateway_sat_devices[handover_target_sat],
                   "handover handover needs qualified satellite interfaces");
            for (unsigned terminal = 0; terminal < terminal_rsus.size(); ++terminal) {
            const auto owner = terminal_rsus.at(terminal);
            const std::int64_t request_us = handover_request_us + 200000LL * terminal;
            handover_states[owner] = "connected_old";
            auto set_state = [owner](const std::string& state) {
                handover_states[owner] = state;
                if (owner == rsu_id) handover_state = state;
            };
            auto ut_node = satellite->UtNodes().Get(terminal);
            n::Ptr<n::SatNetDevice> ut_radio;
            for (unsigned i = 0; i < ut_node->GetNDevices(); ++i)
                if (auto candidate = n::DynamicCast<n::SatNetDevice>(ut_node->GetDevice(i))) {
                    ensure(!ut_radio, "handover requires exactly one UT satellite radio");
                    ut_radio = candidate;
                }
            ensure(ut_radio != nullptr, "handover single UT satellite radio absent");
            auto ut_mac = n::DynamicCast<n::SatUtMac>(ut_radio->GetMac());
            auto ut_phy = n::DynamicCast<n::SatUtPhy>(ut_radio->GetPhy());
            auto ut_llc = n::DynamicCast<n::SatUtLlc>(ut_radio->GetLlc());
            auto observer = ut_node->GetObject<n::SatMobilityObserver>();
            auto from_sat = n::DynamicCast<n::SatGeoNetDevice>(
                satellite->GeoSatNodes().Get(initial_serving_sat)->GetDevice(0));
            auto to_sat = n::DynamicCast<n::SatGeoNetDevice>(
                satellite->GeoSatNodes().Get(handover_target_sat)->GetDevice(0));
            auto ncc = satellite->GetBeamHelper()->GetNcc();
            auto from_sched = ncc->GetBeamScheduler(initial_serving_sat, handover_beam);
            auto to_sched = ncc->GetBeamScheduler(handover_target_sat, handover_beam);
            const auto ut_mac_addr = n::Mac48Address::ConvertFrom(ut_radio->GetAddress());
            ensure(ut_mac && ut_phy && ut_llc && observer && from_sat && to_sat &&
                   from_sched && to_sched && from_sched->HasUt(ut_mac_addr) &&
                   !to_sched->HasUt(ut_mac_addr), "handover initial one-UT membership invalid");
            const auto from_user = n::Mac48Address::ConvertFrom(
                from_sat->GetUserMac(handover_beam)->GetAddress());
            const auto to_user = n::Mac48Address::ConvertFrom(
                to_sat->GetUserMac(handover_beam)->GetAddress());
            // Samotný natívny handover presunie ten istý UT medzi plánovačmi lúčov, zmení
            // PHY/MAC/LLC adresy a časovanie, aktualizuje obsluhujúci satelit vo fyzikálnej
            // podmienke a preverí konzistentný stav. Nepridáva druhý paralelný terminál.
            auto move = [=](bool to_target) {
                auto old_sat = to_target ? from_sat : to_sat;
                auto new_sat = to_target ? to_sat : from_sat;
                auto old_sched = to_target ? from_sched : to_sched;
                auto new_sched = to_target ? to_sched : from_sched;
                const unsigned target = to_target ? handover_target_sat : initial_serving_sat;
                const auto target_user = to_target ? to_user : from_user;
                ensure(old_sched->HasUt(ut_mac_addr) && !new_sched->HasUt(ut_mac_addr),
                       "handover handover scheduler membership invalid");
                old_sched->TransferUtToBeam(ut_mac_addr, new_sched);
                old_sat->DisconnectUt(ut_mac_addr);
                new_sat->ConnectUt(ut_mac_addr);
                ut_phy->PerformSatelliteHandover(target, handover_beam);
                ut_mac->SetSatelliteAndBeamId(target, handover_beam);
                if (satellite_condition) satellite_condition->SetServing(owner,target);
                ut_mac->SetSatelliteAddress(target_user);
                ut_llc->SetSatelliteAddress(target_user);
                observer->UpdateSatelliteMobility(
                    satellite->GeoSatNodes().Get(target)->GetObject<n::SatMobilityModel>());
                satellite->GetUserHelper()->UpdateUtRoutes(
                    ut_radio->GetAddress(), ut_mac->GetGwAddress());
                observer->ObserveTimingAdvance(
                    satellite->GetBeamHelper()->GetPropagationDelayModel(
                        target, handover_beam, n::SatEnums::RETURN_USER_CH),
                    satellite->GetBeamHelper()->GetPropagationDelayModel(
                        return_route_new_sat, handover_beam, n::SatEnums::RETURN_FEEDER_CH),
                    satellite->GwNodes().Get(0)->GetObject<n::SatMobilityModel>());
                ensure(ut_mac->GetSatId() == target && ut_phy->GetSatId() == target &&
                       new_sched->HasUt(ut_mac_addr) && !old_sched->HasUt(ut_mac_addr),
                       "handover post-handover one-UT state invalid");
                std::cout << "HANDOVER_MOVE_US=" << n::Simulator::Now().GetMicroSeconds()
                          << " SAT=" << target << " RSU=" << owner << " UT_IP=" << rsu_sat_addresses.at(owner)
                          << " UT_MAC=" << ut_radio->GetAddress() << '\n';
                std::cout << "HANDOVER_MOVE_MEMBERSHIP_FROM=" << old_sat->GetUtConnected().size()
                          << " TO=" << new_sat->GetUtConnected().size() << '\n';
            };
            n::Simulator::Schedule(n::MicroSeconds(request_us), [=] {
                const bool candidate = handover_case != "no_candidate";
                const bool beam = handover_case != "no_beam" &&
                                  to_sat->GetUserMac().count(handover_beam);
                const bool attach = handover_case != "no_attach" && to_sched;
                const bool route = handover_case != "no_route" && model_has_isl;
                if (!candidate || !beam || !attach || !route) {
                    set_state("failed_old");
                    std::cout << "HANDOVER_PREFLIGHT_REJECT_US=" << n::Simulator::Now().GetMicroSeconds()
                              << " CANDIDATE=" << candidate << " BEAM=" << beam
                              << " ATTACH=" << attach << " ROUTE=" << route << '\n';
                } else {
                    set_state("pending");
                    std::cout << "HANDOVER_REQUEST_US=" << n::Simulator::Now().GetMicroSeconds()
                              << " TARGET=" << handover_target_sat << " RSU=" << owner << '\n';
                }
            });
            // Prepnutie sa odloží, kým UT fyzicky vysiela, aby sa nepresúval počas rozbehnutého
            // rámca. Časový limit a následná skúšobná správa rozhodnú, či sa nový link považuje za
            // použiteľný.
            auto safe_move=std::make_shared<std::function<void()>>();
            *safe_move=[=] {
                if (handover_states.at(owner) != "pending") return;
                if (n::Simulator::Now().GetMicroSeconds() >= request_us + 250000) {
                    set_state("failed_old");std::cout<<"SIM_HANDOVER_DEFER_TIMEOUT_US="<<n::Simulator::Now().GetMicroSeconds()<<'\n';return;
                }
                if (ut_phy->GetPhyTx()->IsTransmitting()) {
                    std::cout<<"SIM_DEFER_HANDOVER_US="<<n::Simulator::Now().GetMicroSeconds()<<'\n';
                    n::Simulator::Schedule(n::MicroSeconds(100),*safe_move);return;
                }
                move(true);set_state("await_probe");
            };
            n::Simulator::Schedule(n::MicroSeconds(request_us + 200000),*safe_move);
            n::Simulator::Schedule(n::MicroSeconds(request_us + 250000), [=] {
                if (handover_states.at(owner) != "await_probe") return;
                const std::uint8_t probe[] = {'P','3','P','R'};
                ensure(rsu_satellite_sockets.at(owner)->SendTo(n::Create<n::Packet>(probe, sizeof(probe)), 0,
                           n::InetSocketAddress(gateway_address, report_port)) == 4,
                       "handover probe send failed");
                std::cout << "HANDOVER_PROBE_TX_US=" << n::Simulator::Now().GetMicroSeconds() << '\n';
            });
            auto safe_rollback=std::make_shared<std::function<void()>>();
            *safe_rollback=[=] {
                if (handover_states.at(owner) != "await_probe") return;
                if (n::Simulator::Now().GetMicroSeconds() >= request_us + 2500000) {
                    set_state("rollback_blocked");std::cout<<"SIM_ROLLBACK_TIMEOUT_US="<<n::Simulator::Now().GetMicroSeconds()<<'\n';return;
                }
                if (ut_phy->GetPhyTx()->IsTransmitting()) {
                    n::Simulator::Schedule(n::MicroSeconds(100),*safe_rollback);return;
                }
                move(false);set_state("failed_old");
                std::cout << "SIM_PROBE_TIMEOUT_ROLLBACK_US=" << n::Simulator::Now().GetMicroSeconds() << '\n';
            };
            n::Simulator::Schedule(n::MicroSeconds(request_us + 2000000),*safe_rollback);
            }
        }
        ut_lan_ack_socket = rsu_lan_ack_sockets.at(rsu_id);
        std::vector<std::unique_ptr<Station>> stations;
        for (std::size_t i = 0; i < node_order.size(); ++i)
            stations.emplace_back(std::make_unique<Station>(devices.Get(i), node_order[i],
                tracks.at(node_order[i])));
        // Pred prvým CAM alebo DENM sa kontroluje každé pozemné rádio, RSU terminál, jeho MAC
        // členstvo v plánovači satelitu, brána a aplikačné sockety. Zlyhaná príprava zastaví beh;
        // rádiový výpadok počas pokusu zostáva meraný výsledok.
        // The first application event is at t=0. Every dependency must exist
        // before Simulator::Run; a missing terminal is a startup error, while
        // later RF loss remains a measured outcome of the experiment.
        ensure(stations.size() == node_order.size() && devices.GetN() == node_order.size(),
               "ground radio startup incomplete");
        for (const auto& id : node_order)
            ensure(!tracks.at(id).empty() && tracks.at(id).front().time_us == 0,
                   "vehicle or RSU has no position at experiment t=0");
        if (backhaul_mode == "satellite" && cam_denm_mode) {
            ensure(satellite->GeoSatNodes().GetN() == expected_satellites &&
                   terminal_rsus.size() == active_rsus.size() &&
                   satellite_condition && satellite_condition->Registered() == terminal_rsus.size(),
                   "satellite topology or terminal startup incomplete");
            auto ncc = satellite->GetBeamHelper()->GetNcc();
            ensure(ncc && return_route_new_sat < expected_satellites,
                   "satellite NCC or feeder route absent at t=0");
            auto feeder = n::DynamicCast<n::SatGeoNetDevice>(
                satellite->GeoSatNodes().Get(return_route_new_sat)->GetDevice(0));
            ensure(feeder && !feeder->GetGwConnected().empty(),
                   "feeder satellite has no gateway at t=0");
            for (unsigned i = 0; i < terminal_rsus.size(); ++i) {
                const auto& owner = terminal_rsus[i];
                auto ut_node = satellite->UtNodes().Get(i);
                n::Ptr<n::SatNetDevice> radio;
                for (unsigned device = 0; device < ut_node->GetNDevices(); ++device)
                    if (auto candidate = n::DynamicCast<n::SatNetDevice>(ut_node->GetDevice(device))) {
                        ensure(!radio, "RSU has multiple satellite radios at t=0");
                        radio = candidate;
                    }
                ensure(radio && radio->GetPhy() && radio->GetLlc(),
                       "RSU satellite radio is incomplete at t=0");
                auto mac = n::DynamicCast<n::SatUtMac>(radio->GetMac());
                ensure(mac && mac->GetSatId() < expected_satellites,
                       "RSU terminal has no serving satellite at t=0");
                auto sat_id = mac->GetSatId();
                auto beam = mac->GetBeamId();
                auto scheduler = ncc->GetBeamScheduler(sat_id, beam);
                auto geo = n::DynamicCast<n::SatGeoNetDevice>(
                    satellite->GeoSatNodes().Get(sat_id)->GetDevice(0));
                auto address = n::Mac48Address::ConvertFrom(radio->GetAddress());
                ensure(scheduler && scheduler->HasUt(address) && geo &&
                       geo->GetUtConnected().count(address) == 1,
                       "RSU terminal is absent from its satellite scheduler at t=0");
                ensure(rsu_lan_addresses.count(owner) && rsu_sat_addresses.count(owner) &&
                       denm_rsu_uplink_sockets.count(owner) && denm_ut_sat_sockets.count(owner),
                       "RSU LAN or satellite application socket is absent at t=0");
            }
            ensure(denm_gateway_socket && gateway_ack_socket,
                   "gateway application socket is absent at t=0");
            std::cout << "READY_AT_T0 TERMINALS=" << terminal_rsus.size()
                      << " SATELLITES=" << expected_satellites << '\n';
        }
        if (cam_denm_mode)
            for (const auto& station : stations) denm_stations.emplace(station->id(), station.get());
        if (backhaul_mode == "satellite" && cam_denm_mode) {
            unsigned hooked = 0;
            for (unsigned node_id = 0; node_id < n::NodeList::GetNNodes(); ++node_id) {
                auto node = n::NodeList::GetNode(node_id);
                for (unsigned device_id = 0; device_id < node->GetNDevices(); ++device_id) {
                    auto radio = n::DynamicCast<n::SatNetDevice>(node->GetDevice(device_id));
                    if (!radio) continue;
                    const auto type = n::DynamicCast<n::SatUtMac>(radio->GetMac()) ? "UT" : "GW";
                    ensure(radio->TraceConnectWithoutContext("Tx", n::MakeBoundCallback(
                        &on_satellite_ip_tx, std::string(type), node->GetId())),
                        "SNS-3 satellite IP Tx trace unavailable");
                    ++hooked;
                }
            }
            ensure(hooked >= terminal_rsus.size() + 1,
                   "SNS-3 satellite IP trace misses UT or GW devices");
        }
        for (std::size_t i = 0; i < stations.size(); ++i) {
            auto wifi_phy = n::DynamicCast<n::WifiNetDevice>(devices.Get(i))->GetPhy();
            ensure(wifi_phy->GetState()->TraceConnectWithoutContext("State",
                       n::MakeCallback(&Station::on_state, stations[i].get())),
                   "ground radio PHY state trace absent");
            ensure(wifi_phy->TraceConnectWithoutContext("PhyRxDrop",
                       n::MakeCallback(&Station::on_drop, stations[i].get())),
                   "ground radio PHY drop trace absent");
        }
        for (std::size_t sample = 0; sample < cam_count; ++sample) {
            for (std::size_t i = 0; i < node_order.size(); ++i) {
                const auto w = tracks.at(node_order[i])[sample];
                auto station = stations[i].get();
                n::Simulator::Schedule(n::MicroSeconds(w.time_us),
                                       [station, w] { station->update_position(w); });
            }
            if (building_channel) {
                const auto when = tracks.at(node_order.front())[sample].time_us;
                n::Simulator::Schedule(n::MicroSeconds(when), [&radio_nodes, when] {
                    n::Ptr<n::ChannelConditionModel> condition = radio_mode == "urban_osm_building" ?
                        n::Ptr<n::ChannelConditionModel>(osm_condition) :
                        n::Ptr<n::ChannelConditionModel>(n::CreateObject<n::BuildingsChannelConditionModel>());
                    for (std::size_t i = 0; i < node_order.size(); ++i) {
                        if (tracks.at(node_order[i]).front().kind != "car") continue;
                        for (std::size_t j = 0; j < node_order.size(); ++j) {
                            if (tracks.at(node_order[j]).front().kind != "rsu") continue;
                            auto a = radio_nodes.Get(i)->GetObject<n::MobilityModel>();
                            auto b = radio_nodes.Get(j)->GetObject<n::MobilityModel>();
                            building_trace << when << ',' << node_order[i] << ',' << node_order[j]
                                           << ',' << int(condition->GetChannelCondition(a, b)->IsNlos()) << '\n';
                        }
                    }
                });
            }
            for (std::size_t i = 0; i < node_order.size(); ++i) {
                const auto w = tracks.at(node_order[i])[sample];
                if (w.kind != "car") continue;
                auto station = stations[i].get();
                n::Simulator::Schedule(n::MicroSeconds(w.time_us + phase_us * (i + 1)),
                                       [station, w] { station->check(w); });
            }
        }
        if (cam_denm_mode) {
            for (const auto& event : denm_events) {
                auto source = denm_stations.at(event.source_id);
                n::Simulator::Schedule(n::MicroSeconds(event.time_us),
                    [source, event] { source->send_denm(event); });
            }
        }
        unsigned satellite_channels = 0;
        for (unsigned i = 0; i < n::ChannelList::GetNChannels(); ++i) {
            auto channel = n::DynamicCast<n::SatChannel>(n::ChannelList::GetChannel(i));
            if (!channel) continue;
            ensure(channel->TraceConnectWithoutContext("EarthOccultationDrop",
                       n::MakeCallback(&on_native_satellite_mask_drop)),
                   "SNS-3 native satellite visibility trace absent");
            ++satellite_channels;
        }
        ensure(!leo_reference || satellite_channels > 0,
               "SNS-3 native satellite channels absent");
        std::cout << "SIM_NATIVE_SAT_CHANNELS=" << satellite_channels
                  << " MASK_DEG=" << satellite_mask_deg << '\n';
        n::Simulator::Stop(n::MicroSeconds(simulation_end_us));
        n::Singleton<n::SatRxPowerOutputTraceContainer>::Get()->EnableFigureOutput(false);
        n::Singleton<n::SatRxPowerOutputTraceContainer>::Get()->Reset();
        // Od tohto okamihu ns-3 vykoná všetky naplánované udalosti: pohyb, tvorbu správ, rádio,
        // SNS-3 a príjem. Výpisy a CSV vznikajú z callbackov týchto udalostí. Po návrate treba
        // Simulator::Destroy() a nezávislý verifier.
        // `Run()` spustí front udalostí ns-3. Ak je v čase t naplánovaný pohyb, odoslanie CAM
        // alebo rádiový príjem, ns-3 ho vykoná v určenom poradí. Po skončení sa výsledok nemôže
        // považovať za úspešný len podľa návratového kódu procesu; Python checker overuje
        // konkrétne raw stopy a bajty.
        n::Simulator::Run();
        unsigned total_tx = 0, total_rx = 0, gn_drop_total = 0;
        for (const auto& station : stations) {
            total_tx += station->l2_tx();
            total_rx += station->cam_rx();
            gn_drop_total += station->gn_drops();
        }
        ensure(total_tx == cam_event_by_key.size() && gn_drop_total == 0,
               "ground radio CAM TX identity/GN count mismatch");
        if (!cam_denm_mode) for (const auto& [key, cam_identity] : cam_event_by_key) {
            auto report = report_by_cam.find(key);
            if (report == report_by_cam.end())
                log_event("dropped", rsu_id, cam_identity, "radio_or_rsu_missing");
            else if (!block_satellite && !forward_dropped_ids.count(report->second) &&
                     !pending_dropped_ids.count(report->second) &&
                     !satellite_forward_isl_drops.count(report->second) &&
                     !accepted_reports.count(report->second))
                log_event("dropped", "ut-user", report->second,
                          backhaul_mode == "satellite" && !model_has_isl ?
                          "no_isl_path" : "remote_path_loss");
        }
        std::ofstream delivery(delivery_file);
        ensure(delivery.good(), "delivery CSV open failed");
        delivery << "recipient_id,kind,expected_cam,gn_rx,decoded_cam,gn_drop,control,drop_reason\n";
        const unsigned primary_sent = stations.front()->l2_tx();
        for (std::size_t i = 0; i < stations.size(); ++i) {
            auto& receiver = stations[i];
            const auto& track = tracks.at(receiver->id());
            const char* reason = receiver->primary_cam_rx() == primary_sent ? "none" : "unknown";
            delivery << receiver->id() << ',' << track.front().kind << ',' << primary_sent << ','
                     << receiver->l2_rx() << ',' << receiver->primary_cam_rx() << ','
                     << receiver->gn_drops() << ',' << (block_satellite ? "blocked_satellite" : "positive")
                     << ',' << reason << '\n';
        }
        delivery.close();
        if (!cam_denm_mode) ensure(reports_created == report_by_cam.size() &&
               reports_offered + forward_queue_drops == reports_created && forward_queue.empty() &&
               satellite_held_reports.empty() &&
               satellite_forward_isl_drops.size() <= satellite_offered &&
               satellite_reverse_isl_drops.size() <= gateway_ack_sent &&
               (backhaul_mode == "local" ? ut_received == 0 : ut_received == reports_offered) &&
               satellite_offered == (backhaul_mode == "local" || block_satellite ? 0U :
                                     ut_received - pending_report_drops) &&
               server_accepted <= reports_offered && server_rejected == 0 &&
               (backhaul_mode != "satellite" || model_has_isl || server_accepted == 0) &&
               gateway_ack_sent == (no_return_route ? 0U : server_accepted) &&
               isl_ack_receives <= gateway_ack_sent * expected_satellites &&
               ut_ack_received <= gateway_ack_sent &&
               rsu_ack_received <= gateway_ack_sent &&
               reverse_queue.empty() && reverse_queue_drops <= rsu_ack_received &&
               car_i2v_received <= rsu_ack_received,
               "backhaul RSU/queue/UT/backhaul counts disagree with control");
        const char* case_label = block_satellite ? "blocked" :
                                 no_return_route ? "no_return_route" :
                                 model_has_isl ? "positive" : "no_isl";
        const unsigned background_tx = total_tx - primary_sent;
        ensure(background_tx > 0, "ground radio requires actual concurrent CAM senders");
        if (cam_denm_mode) {
            ensure(reports_created == 0 && server_accepted == 0 && gateway_ack_sent == 0 &&
                   car_i2v_received == 0, "obsolete application message emitted in CAM/DENM mode");
            std::cout << "APPLICATION_MODE=CAM_DENM DENM_EVENTS=" << denm_events.size()
                      << " DENM_TARGET_RSU=" << denm_target_rsu << '\n';
        }
        std::cout << "GROUND_NODES=" << node_order.size() << " CAM_TX=" << total_tx
                  << " CAM_RX=" << total_rx << " PHY_DROPS=" << integrated_phy_drops
                  << " GN_DROPS=" << gn_drop_total << " DCC=" << dcc_enabled
                  << " RADIO=" << radio_mode << " SHADOWING=" << radio_shadowing
                  << " TX_POWER_DBM="
                  << std::setprecision(12) << radio_power_dbm
                  << " RX_NOISE_FIGURE_DB=" << radio_noise_figure_db
                  << " PHASE_US=" << phase_us << " SEED=" << seed << " RUN=" << ns3_run
                  << " DCC_LOW_CBR=" << dcc_low_cbr << " DCC_HIGH_CBR=" << dcc_high_cbr
                  << " DCC_MID_MS=" << dcc_mid_ms << " DCC_HIGH_MS=" << dcc_high_ms << '\n';
        std::cout << "CASE=" << case_label
                  << " NODES=" << node_order.size() << " CAM_TX=" << total_tx
                  << " CAM_RX_TOTAL=" << total_rx << " RSU_REPORTS_CREATED=" << reports_created
                  << " BACKGROUND_CAM_TX=" << background_tx
                  << " RADIO_MODE=" << radio_mode
                  << " WIFI_PHY_DROPS=" << wifi_phy_drops << " LAN_DROPS=" << lan_drops
                  << " LAN_OFFERED=" << reports_offered << " UT_RECEIVED=" << ut_received
                  << " SAT_OFFERED=" << satellite_offered << " GATEWAY_ACCEPT=" << server_accepted
                  << " ISL_REPORT_RX=" << isl_report_receives
                  << " GW_GRA1_TX=" << gateway_ack_sent
                  << " ISL_GRA1_RX=" << isl_ack_receives
                  << " UT_GRA1_RX=" << ut_ack_received
                  << " RSU_GRA1_RX=" << rsu_ack_received
                  << " CAR_I2V1_RX=" << car_i2v_received
                  << " BACKHAUL_MODE=" << backhaul_mode
                  << " ACTIVE_RSUS=" << active_rsus.size()
                  << " FORWARD_QUEUE_DROPS=" << forward_queue_drops
                  << " REVERSE_QUEUE_DROPS=" << reverse_queue_drops
                  << " SATELLITES=" << expected_satellites
                  << " HANDOVER_HANDOVER_CASE=" << handover_case
                  << " HANDOVER_STATE=" << handover_state
                  << " HANDOVER_PENDING_DROPS=" << pending_report_drops
                  << " HANDOVER_PROBE_GATEWAY=" << probe_reached_gateway
                  << " HANDOVER_PROBE_RETURN=" << probe_returned
                  << " SATELLITE_ISL_FORWARD_DROPS=" << satellite_forward_isl_drops.size()
                  << " SATELLITE_ISL_REVERSE_DROPS=" << satellite_reverse_isl_drops.size()
                  << " SATELLITE_OTHER_FORWARD_DROPS=" << satellite_other_forward_drops
                  << " SATELLITE_OTHER_REVERSE_DROPS=" << satellite_other_reverse_drops
                  << " SATELLITE_BURST=" << satellite_burst
                  << " SEED=" << seed << " RUN=" << ns3_run << "\n";
        n::Simulator::Destroy();
        bytes_trace.close(); mobility_trace.close(); decoded_trace.close(); event_trace.close();
        cam_trace.close(); phy_state_trace.close(); dcc_trace.close(); rx_trace.close();
        phy_drop_trace.close(); identity_trace.close(); selection_trace.close(); queue_trace.close();
    } catch (const std::exception& e) {
        std::cerr << "SIMULATOR_NATIVE_FAILED=" << e.what() << '\n';
        n::Simulator::Destroy();
        return 1;
    }
}
