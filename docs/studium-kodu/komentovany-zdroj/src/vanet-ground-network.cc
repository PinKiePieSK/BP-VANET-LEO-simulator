// Pozemný paketový engine používa pre CAM a výšku antény hodnoty odovzdané scenárom; rozhodnutia
// ostávajú v raw DCC stope.
// Ground CAM/DENM packets: Vanetza GN/BTP over ns-3 802.11p OCB.
// The configurable CBR feedback changes the minimum CAM interval.
#include <ns3/core-module.h>
#include <ns3/network-module.h>
#include <ns3/wifi-module.h>
#include <ns3/wave-module.h>
#include <ns3/mobility-module.h>
#include <ns3/buildings-module.h>
#include <ns3/propagation-module.h>
#include <ns3/wifi-phy-state-helper.h>
#include "ground-building-condition.h"
#include "rsu-radio-config.h"
#include <vanetza/asn1/cam.hpp>
#include <vanetza/asn1/denm.hpp>
#include <vanetza/asn1/support/INTEGER.h>
#include <openssl/sha.h>
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
#include <cstdlib>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <sstream>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
namespace n = ns3;
namespace v = vanetza;
// `need()` zastaví beh, ak povinná podmienka nie je splnená.
static void need(bool ok, const char* why) { if (!ok) throw std::runtime_error(why); }
static std::string runtime_origin="2026-10-22 12:45:00";

// Adaptér časovania Vanetza na ns-3 pre čisto pozemný beh. Vďaka nemu sa čas hlavičiek a volanie
// udalostí držia rovnakých simulačných hodín ako Wi-Fi/OCB rádio.
class Runtime final : public v::Runtime {
public:
    Runtime() : origin_(v::Clock::at(runtime_origin)) {}
    // `schedule()` preloží požiadavku Vanetza na plánovanú udalosť v hodinách ns-3.
    void schedule(v::Clock::time_point tp, const Callback& cb, const void* scope = nullptr) override {
        auto us = std::chrono::duration_cast<std::chrono::microseconds>(tp - now()).count();
        if (us < 0) us = 0;
        events_.push_back({scope, n::Simulator::Schedule(n::MicroSeconds(us), [cb,tp] { cb(tp); })});
    }
    // `schedule()` preloží požiadavku Vanetza na plánovanú udalosť v hodinách ns-3.
    void schedule(v::Clock::duration d, const Callback& cb, const void* scope = nullptr) override { schedule(now()+d, cb, scope); }
    // `cancel()` zruší ešte nevykonané časované udalosti.
    void cancel(const void* scope) override { for (auto& item : events_) if (item.first == scope) item.second.Cancel(); }
    // `now()` vráti aktuálny simulačný čas prevedený na čas Vanetza.
    v::Clock::time_point now() const override { return origin_ + v::Clock::duration(n::Simulator::Now().GetMicroSeconds()); }
private:
    v::Clock::time_point origin_;
    std::vector<std::pair<const void*,n::EventId>> events_;
};

// Pozemná časová vzorka nesie ID stanice, polohu, rýchlosť a čas. Hodnoty vo waypointoch sú už
// prevedené do jednotiek, ktoré pri tvorbe CAM očakáva Vanetza a pri pohybe ns-3.
struct Sample {
    std::string id, kind;
    unsigned station, index;
    std::int64_t us;
    double x, y;
    long lat, lon, alt, speed, heading, gdt, accel, yaw, curvature, length, width, lights;
};
// Mapa ID uzla na vzorky polohy. Každé auto dostane vlastný sled; RSU používa pevný bod. Časové
// vzorky sa nevyhodnocujú pri kreslení UI, ale pri plánovaných udalostiach ns-3.
static std::map<std::string,std::vector<Sample>> tracks;
static std::vector<std::string> order;
static std::set<std::string> ground_off_cars, cars_only, ground_off_rsus;
static std::map<unsigned,std::string> station_owner;
static std::map<std::pair<unsigned,long>,std::vector<std::uint8_t>> sent_cam;
// Zdrojové auto je súčasťou každej udalosti. Vlastný program iba plánuje vznik správy; Vanetza ju
// kóduje a ns-3 vykonáva pozemný rádiový prenos.
struct DenmEvent {std::int64_t time_us;std::string source_id;unsigned sequence;std::string operation;unsigned validity_s,radius_m,repetition_ms;};
static std::vector<DenmEvent> denm_events;
static std::map<std::pair<unsigned,unsigned>,long> denm_detection_ms;
static std::ofstream packet_trace;
static std::ofstream cam_trace, phy_trace, decision_trace, rx_trace, building_trace, phy_drop_trace;
static unsigned phy_drops = 0;
static std::uint64_t event_sequence = 0;
static bool building_mode = false;
static n::Ptr<groundradio::OSMBuildingCondition> osm_condition;
struct BoxInput {std::string id;double xmin,xmax,ymin,ymax,zmin,zmax;};
static std::vector<BoxInput> boxes;
// Prah pohybu a geometria antén menia odosielanie alebo šírenie signálu, preto sú explicitnými
// vstupmi behu.
static double cam_distance_m=4.0,cam_speed_mps=0.5,cam_heading_deg=4.0;
static unsigned cam_low_frequency_ms=500,cam_tgen_max_ms=1000,cam_periodic_repeat=3;
static double car_antenna_height_m=1.5,rsu_antenna_min_height_m=5.0,rsu_roof_clearance_m=2.0;
static double radio_height(const Sample& w){
    if(w.kind!="rsu"){
        const auto* profile=rsuradio::find_car(w.id);
        return profile ? profile->height : car_antenna_height_m;
    }
    const auto* profile=rsuradio::find(w.id);
    if(profile&&profile->height>=0)return profile->height;
    return std::max(rsu_antenna_min_height_m,osm_condition ? osm_condition->RoofAt(w.x,w.y)+rsu_roof_clearance_m : rsu_antenna_min_height_m);
}
// `load_boxes()` načíta dáta zo súboru alebo pamäte.
static void load_boxes(const std::string& path){
    std::ifstream file(path);if(!file)throw std::runtime_error("building CSV missing: "+path);
    std::string line;std::getline(file,line);
    need(line=="id,x_min,x_max,y_min,y_max,z_min,z_max","building CSV header invalid");
    while(std::getline(file,line)){
        if(line.empty())continue;std::stringstream ss(line);std::vector<std::string> c;std::string x;
        while(std::getline(ss,x,','))c.push_back(x);need(c.size()==7,"building row invalid");
        BoxInput b{c[0],std::stod(c[1]),std::stod(c[2]),std::stod(c[3]),std::stod(c[4]),std::stod(c[5]),std::stod(c[6])};
        need(b.xmin<b.xmax&&b.ymin<b.ymax&&b.zmin<b.zmax,"building box invalid");boxes.push_back(b);
    }
    need(!boxes.empty()&&boxes.size()<=100,"building count invalid");
}
// `hex()` prevedie raw bajty na hexadecimálny text.
static std::string hex(const std::vector<std::uint8_t>& b) {
    static const char* digits="0123456789abcdef"; std::string s; s.reserve(2*b.size());
    for (auto v:b) {s+=digits[v>>4];s+=digits[v&15];} return s;
}
static void packet_row(const char* stage,const std::string& node,std::uint64_t id,
                       const std::vector<std::uint8_t>& raw){
    packet_trace<<stage<<','<<node<<','<<std::hex<<std::setw(16)<<std::setfill('0')<<id
                <<std::dec<<','<<n::Simulator::Now().GetMicroSeconds()<<','<<raw.size()<<','<<hex(raw)<<'\n';
}
// `denm_id()` odvodí identitu konkrétnej verzie výstrahy DENM.
static std::uint64_t denm_id(const v::asn1::r2::Denm& denm){
    long reference=0;need(asn_INTEGER2long(&denm->denm.management.referenceTime,&reference)==0,"DENM reference time invalid");
    const auto& action=denm->denm.management.actionId;
    const std::string key="denm:"+std::to_string(action.originatingStationId)+':'+
        std::to_string(action.sequenceNumber)+':'+std::to_string(reference);
    std::array<unsigned char,SHA256_DIGEST_LENGTH> hash{};
    SHA256(reinterpret_cast<const unsigned char*>(key.data()),key.size(),hash.data());
    std::uint64_t id=0;for(unsigned i=0;i<8;++i)id=(id<<8)|hash[i];return id;
}
// `decode_denm()` prekladá raw bajty na významové polia.
static v::asn1::r2::Denm decode_denm(const std::vector<std::uint8_t>& raw){
    v::asn1::r2::Denm denm;need(denm.decode(raw)&&denm.validate()&&
        denm->header.protocolVersion==2&&denm->header.messageId==1,"DENM UPER invalid");return denm;
}
static long its_ms(std::int64_t time_us){
    return std::chrono::duration_cast<std::chrono::milliseconds>(
        v::Clock::at(runtime_origin).time_since_epoch()).count()+time_us/1000;
}
// Vytvorí normovanú výstrahu z udalosti scenára. Toto je aplikačná tvorba obsahu; prijatie sa
// osobitne preukazuje v ns-3/Vanetza stopách.
static v::asn1::r2::Denm make_denm(const Sample& w,const Sample& previous,const DenmEvent& e){
    v::asn1::r2::Denm denm;denm->header.protocolVersion=2;denm->header.messageId=1;
    denm->header.stationId=w.station;auto& m=denm->denm.management;
    m.actionId.originatingStationId=w.station;m.actionId.sequenceNumber=e.sequence;
    const long detection=denm_detection_ms.emplace(std::make_pair(w.station,e.sequence),its_ms(e.time_us)).first->second;
    need(asn_long2INTEGER(&m.detectionTime,detection)==0&&
         asn_long2INTEGER(&m.referenceTime,its_ms(e.time_us))==0,"DENM ITS timestamp invalid");
    if(e.operation=="cancel"){
        m.termination=v::asn1::allocate<Vanetza_ITS2_Termination_t>();
        *m.termination=Vanetza_ITS2_Termination_isCancellation;
    }
    auto& p=m.eventPosition;p.latitude=w.lat;p.longitude=w.lon;
    p.positionConfidenceEllipse.semiMajorConfidence=Vanetza_ITS2_SemiAxisLength_unavailable;
    p.positionConfidenceEllipse.semiMinorConfidence=Vanetza_ITS2_SemiAxisLength_unavailable;
    p.positionConfidenceEllipse.semiMajorOrientation=Vanetza_ITS2_Wgs84AngleValue_unavailable;
    p.altitude.altitudeValue=w.alt;p.altitude.altitudeConfidence=Vanetza_ITS2_AltitudeConfidence_unavailable;
    m.stationType=Vanetza_ITS2_TrafficParticipantType_passengerCar;
    m.validityDuration=v::asn1::allocate<Vanetza_ITS2_DeltaTimeSecond_t>();*m.validityDuration=e.validity_s;
    if(e.repetition_ms){m.transmissionInterval=v::asn1::allocate<Vanetza_ITS2_DeltaTimeMilliSecondPositive_t>();
        *m.transmissionInterval=e.repetition_ms;}
    denm->denm.situation=v::asn1::allocate<Vanetza_ITS2_SituationContainer_t>();
    denm->denm.situation->informationQuality=0;
    denm->denm.situation->eventType.ccAndScc.present=Vanetza_ITS2_CauseCodeChoice_PR_trafficCondition1;
    denm->denm.situation->eventType.ccAndScc.choice.trafficCondition1=
        Vanetza_ITS2_TrafficConditionSubCauseCode_trafficJam;
    denm->denm.location=v::asn1::allocate<Vanetza_ITS2_LocationContainer_t>();
    auto* path=v::asn1::allocate<Vanetza_ITS2_Path_t>();
    auto* point=v::asn1::allocate<Vanetza_ITS2_PathPoint_t>();
    point->pathPosition.deltaLatitude=std::clamp(previous.lat-w.lat,-131071L,131071L);
    point->pathPosition.deltaLongitude=std::clamp(previous.lon-w.lon,-131071L,131071L);
    point->pathPosition.deltaAltitude=std::clamp(previous.alt-w.alt,-127L,127L);
    need(ASN_SEQUENCE_ADD(&path->list,point)==0&&
         ASN_SEQUENCE_ADD(&denm->denm.location->detectionZonesToEventPosition.list,path)==0,
         "DENM detection path invalid");
    std::string error;need(denm.validate(error),error.c_str());return denm;
}
// `load()` načíta dáta zo súboru alebo pamäte.
static void load(const std::string& path) {
    std::ifstream file(path); if(!file)throw std::runtime_error("waypoint CSV missing: "+path); std::string line; std::getline(file,line);
    need(line=="node_id,station_id,kind,index,time_us,utc,x_m,y_m,latitude_e7,longitude_e7,altitude_cm,speed_cmps,heading_decideg,generation_delta_ms,acceleration_dmps2,yaw_rate_cdegps,curvature_1e4,vehicle_length_dm,vehicle_width_dm,exterior_lights_bits", "bad waypoint header");
    while (std::getline(file,line)) {
        if (line.empty()) continue;
        std::stringstream ss(line); std::vector<std::string> c; std::string x;
        while(std::getline(ss,x,',')) c.push_back(x); need(c.size()==20,"bad waypoint row");
        Sample w{c[0],c[2],unsigned(std::stoul(c[1])),unsigned(std::stoul(c[3])),std::stoll(c[4]),
                 std::stod(c[6]),std::stod(c[7]),std::stol(c[8]),std::stol(c[9]),std::stol(c[10]),
                 std::stol(c[11]),std::stol(c[12]),std::stol(c[13]),std::stol(c[14]),
                 std::stol(c[15]),std::stol(c[16]),std::stol(c[17]),std::stol(c[18]),std::stol(c[19])};
        auto& t=tracks[w.id]; if(t.empty()) order.push_back(w.id);
        need(w.index==t.size() && (w.kind=="car" || w.kind=="rsu"),"unordered sample"); t.push_back(w);
    }
    need(order.size()>=2,"at least two radio participants required");
    const auto& first=tracks.at(order.front()); need(first.size()>=20 && first.size()<=1200,"sample count outside 20..1200");
    for(const auto& id:order) {
        const auto& t=tracks.at(id); need(t.size()==first.size(),"unequal tracks");
        need(station_owner.emplace(t.front().station,id).second,"duplicate station identity");
        for(size_t i=0;i<t.size();++i) need(t[i].us==first[i].us && t[i].station==1001+(&id-&order[0]),"unaligned tracks");
    }
    for(size_t i=1;i<first.size();++i) need(first[i].us-first[i-1].us==100000,"ground model requires 100ms FCD");
}
// `policy_ids()` načíta zoznam uzlov, na ktoré sa vzťahuje vybraná komunikačná politika.
static std::set<std::string> policy_ids(const char* key,const char* kind){
    std::set<std::string> ids;const char* raw=std::getenv(key);if(!raw||!*raw)return ids;
    std::stringstream stream(raw);std::string id;
    while(std::getline(stream,id,',')){
        need(tracks.count(id)&&tracks.at(id).front().kind==kind,"policy node missing or wrong kind");
        need(ids.insert(id).second,"duplicate node policy ID");
    }
    return ids;
}
// `mac_of()` získa MAC adresu pozemného zariadenia.
static v::MacAddress mac_of(n::Ptr<n::NetDevice> d) {
    std::ostringstream s;s<<n::Mac48Address::ConvertFrom(d->GetAddress()); v::MacAddress m;
    need(v::parse_mac_address(s.str(),m),"MAC parse failed");return m;
}
// Naplní ETSI polia CAM zo SUMO vzorky a zakóduje ich cez Vanetza UPER. Skontroluj jednotky:
// zemepisné súradnice sú v celočíselnom tvare, rýchlosť a smer v mierkach definovaných normou.
static v::ByteBuffer encode_cam(const Sample& w,long gdt,bool low_frequency) {
    v::asn1::r2::Cam cam; cam->header.protocolVersion=2;cam->header.messageId=2;cam->header.stationId=w.station;
    cam->cam.generationDeltaTime=gdt;
    auto& cp=cam->cam.camParameters;cp.basicContainer.stationType=Vanetza_ITS2_TrafficParticipantType_passengerCar;
    auto& p=cp.basicContainer.referencePosition;p.latitude=w.lat;p.longitude=w.lon;
    p.positionConfidenceEllipse.semiMajorAxisLength=Vanetza_ITS2_SemiAxisLength_unavailable;
    p.positionConfidenceEllipse.semiMinorAxisLength=Vanetza_ITS2_SemiAxisLength_unavailable;
    p.positionConfidenceEllipse.semiMajorAxisOrientation=Vanetza_ITS2_Wgs84AngleValue_unavailable;
    p.altitude.altitudeValue=w.alt;
    p.altitude.altitudeConfidence=Vanetza_ITS2_AltitudeConfidence_unavailable;
    cp.highFrequencyContainer.present=Vanetza_ITS2_HighFrequencyContainer_PR_basicVehicleContainerHighFrequency;
    auto& q=cp.highFrequencyContainer.choice.basicVehicleContainerHighFrequency;
    q.heading.headingValue=w.heading;q.heading.headingConfidence=127;
    q.speed.speedValue=w.speed;q.speed.speedConfidence=127;q.driveDirection=Vanetza_ITS2_DriveDirection_forward;
    q.vehicleLength.vehicleLengthValue=w.length;q.vehicleLength.vehicleLengthConfidenceIndication=0;q.vehicleWidth=w.width;
    // Pozemná vetva vkladá do ASN.1 skutočné vzorky modelu SUMO; presnosti senzorov ostávajú
    // unavailable. Dĺžka a šírka pochádzajú z typu auta. História trasy je vzorka spred 500 ms
    // relatívna k aktuálnej polohe.
    q.longitudinalAcceleration.value=w.accel;q.longitudinalAcceleration.confidence=102;
    q.curvature.curvatureValue=w.curvature;q.curvature.curvatureConfidence=7;
    q.curvatureCalculationMode=w.curvature==1023?Vanetza_ITS2_CurvatureCalculationMode_unavailable:Vanetza_ITS2_CurvatureCalculationMode_yawRateUsed;
    q.yawRate.yawRateValue=w.yaw;q.yawRate.yawRateConfidence=8;
    if(low_frequency){
        cp.lowFrequencyContainer=static_cast<Vanetza_ITS2_LowFrequencyContainer_t*>(
            std::calloc(1,sizeof(Vanetza_ITS2_LowFrequencyContainer_t)));
        need(cp.lowFrequencyContainer,"CAM low frequency allocation failed");
        cp.lowFrequencyContainer->present=Vanetza_ITS2_LowFrequencyContainer_PR_basicVehicleContainerLowFrequency;
        auto& low=cp.lowFrequencyContainer->choice.basicVehicleContainerLowFrequency;
        low.vehicleRole=Vanetza_ITS2_VehicleRole_default;
        low.exteriorLights.buf=static_cast<std::uint8_t*>(std::calloc(1,1));
        need(low.exteriorLights.buf,"CAM lights allocation failed");
        low.exteriorLights.size=1;low.exteriorLights.bits_unused=0;low.exteriorLights.buf[0]=w.lights;
        // One measured half-second waypoint is encoded relative to the current CAM position.
        if(w.index>=5){
            const auto& prior=tracks.at(w.id).at(w.index-5);
            const long dlat=prior.lat-w.lat,dlon=prior.lon-w.lon,dalt=prior.alt-w.alt;
            if(w.us-prior.us==500000 && std::abs(dlat)<131072 && std::abs(dlon)<131072 && std::abs(dalt)<12800){
                auto* point=static_cast<Vanetza_ITS2_PathPoint_t*>(std::calloc(1,sizeof(Vanetza_ITS2_PathPoint_t)));
                need(point,"CAM path allocation failed");
                point->pathPosition.deltaLatitude=dlat;point->pathPosition.deltaLongitude=dlon;
                point->pathPosition.deltaAltitude=dalt;
                point->pathDeltaTime=static_cast<long*>(std::calloc(1,sizeof(long)));
                need(point->pathDeltaTime,"CAM path time allocation failed");*point->pathDeltaTime=50;
                need(ASN_SEQUENCE_ADD(&low.pathHistory.list,point)==0,"CAM path append failed");
            }
        }
    }
    need(cam.validate(),"CAM invalid");return cam.encode();
}
struct Interval {std::int64_t a,b;};
struct DccPolicy {double low,high;unsigned mid_ms,high_ms;};
// Pozemná ITS stanica: ns-3 zariadenie je skutočný prenosový kanál, Vanetza tvorí
// GeoNetworking/BTP/CAM/DENM. Spätné volania tu spájajú vysielanie, obsadenosť kanála, príjem a
// rozhodnutie DCC.
class Station final : public v::dcc::RequestInterface, public v::btp::IndicationInterface {
public:
    static v::geonet::MIB mib() {v::geonet::MIB m;m.itsGnSecurity=false;m.vanetzaDisableBeaconing=true;return m;}
    Station(n::Ptr<n::NetDevice> d,const std::string& id,const std::vector<Sample>& t,bool dcc,DccPolicy policy)
        : device_(d),id_(id),track_(t),dcc_(dcc),policy_(policy),mac_(mac_of(d)),runtime_(),mib_(mib()),router_(runtime_,mib_) {
        router_.set_address(v::geonet::Address(mac_));router_.set_access_interface(this);
        router_.set_transport_handler(v::geonet::UpperProtocol::BTP_B,&dispatcher_);
        dispatcher_.set_non_interactive_handler(v::btp::ports::CAM,this);
        if(!denm_events.empty())dispatcher_.set_non_interactive_handler(v::btp::ports::DENM,this);
        router_.packet_dropped=[this](v::geonet::Router::PacketDropReason){++gn_drops_;};
        device_->SetReceiveCallback(n::MakeCallback(&Station::receive,this)); update(track_.front());
    }
    // `on_state()` zaznamená čas vysielania, príjmu alebo obsadenosti rádia.
    void on_state(n::Time start,n::Time duration,WifiPhyState state) {
        const auto a=start.GetMicroSeconds(), b=a+duration.GetMicroSeconds();
        if(state==WifiPhyState::TX || state==WifiPhyState::RX || state==WifiPhyState::CCA_BUSY)
            busy_.push_back({a,b});
        phy_trace<<id_<<','<<a<<','<<b<<','<<static_cast<int>(state)<<','
                 <<n::Simulator::Now().GetMicroSeconds()<<','<<++event_sequence<<'\n';
    }
    // `on_drop()` zaznamená dôvod straty prijímaného pozemného rámca.
    void on_drop(n::Ptr<const n::Packet>,n::WifiPhyRxfailureReason reason){
        ++phy_drops;phy_drop_trace<<id_<<','<<n::Simulator::Now().GetMicroSeconds()<<','<<reason<<'\n';
    }
    double cbr(std::int64_t now) {
        const auto from=now-1000000;
        std::vector<Interval> v;
        for(const auto& p:busy_) if(p.b>from && p.a<now) v.push_back({std::max(from,p.a),std::min(now,p.b)});
        std::sort(v.begin(),v.end(),[](auto a,auto b){return a.a<b.a;});
        std::int64_t total=0,end=from;
        for(auto p:v) {if(p.b>end){total+=p.b-std::max(end,p.a);end=p.b;}}
        return double(total)/double(std::max<std::int64_t>(1,std::min<std::int64_t>(1000000,now-track_.front().us)));
    }
    // `update()` aktualizuje existujúci stav.
    void update(const Sample& w) {
        auto mobility=device_->GetNode()->GetObject<n::MobilityModel>();
        mobility->SetPosition(n::Vector(w.x,w.y,radio_height(w)));
        if(building_mode){
            auto info=mobility->GetObject<n::MobilityBuildingInfo>();need(bool(info),"building mobility info missing");
            info->MakeConsistent(mobility);
            need(!info->IsIndoor(),"radio station entered synthetic building");
        }
        v::PositionFix fix;fix.timestamp=runtime_.now();fix.latitude=(w.lat/1e7)*v::units::degrees;
        fix.longitude=(w.lon/1e7)*v::units::degrees;fix.speed=v::units::Velocity::from_value(w.speed/100.0);
        fix.course=v::units::TrueNorth::from_value(w.heading/10.0);
        // No GNSS error model: keep GeoNetworking PAI false instead of claiming 1 m.
        // GeoNetworking PAI vyjadruje dôveryhodnosť polohy. Keďže SUMO nedáva chybu GNSS,
        // používame nedostupnú presnosť; rádio, PHY sadzba a kanál sa ďalej čítajú zo scenára.
        fix.confidence.semi_major=mib_.itsGnPaiInterval;
        fix.confidence.semi_minor=mib_.itsGnPaiInterval;
        router_.update_position(fix);
    }
    // `check()` vykonáva kontrolu podmienok.
    void check(const Sample& w) {
        if(w.kind!="car") return;
        const auto now=n::Simulator::Now().GetMicroSeconds();
        const double load=cbr(now);
        const int minimum=dcc_?(load>=policy_.high?policy_.high_ms:(load>=policy_.low?policy_.mid_ms:100)):100;
        const auto elapsed=last_?now-last_->us:1000000LL;
        const auto dist=last_?std::hypot(w.x-last_->x,w.y-last_->y):0.0;
        const auto speed=last_?std::abs(w.speed-last_->speed)/100.0:0.0;
        const auto angle=last_?std::abs(w.heading-last_->heading)/10.0:0.0;
        const auto heading=std::min(angle,360.0-angle);
        const bool motion=last_ && (dist>cam_distance_m || speed>cam_speed_mps || heading>cam_heading_deg);
        const bool elapsed_ok=elapsed>=minimum*1000LL;
        const bool periodic=elapsed>=tgen_ms_*1000LL;
        const int trigger=!last_?0:(elapsed_ok&&motion?1:(elapsed_ok&&periodic?2:-1));
        const bool send=trigger>=0;
        decision_trace<<id_<<','<<now<<','<<++event_sequence<<','<<std::setprecision(9)<<load<<','<<minimum<<','
                      <<tgen_ms_<<','<<(motion?1:0)<<','<<(periodic?1:0)<<','<<trigger<<','<<int(send)<<','
                      <<dist<<','<<speed<<','<<heading<<'\n';
        if(send){
            send_cam(w);
            if(trigger==1){tgen_ms_=std::min<std::int64_t>(cam_tgen_max_ms,std::max<std::int64_t>(100,elapsed/1000));periodic_count_=0;}
            if(trigger==2 && ++periodic_count_>=cam_periodic_repeat){tgen_ms_=cam_tgen_max_ms;periodic_count_=0;}
            last_=std::make_unique<Sample>(w);last_->us=now;
        }
    }
    void send_cam(const Sample& w) {
        const auto now=n::Simulator::Now().GetMicroSeconds();
        // generationDeltaTime timestamps the sampled reference position, not the later PHY offer.
        const long gdt=w.gdt;
        const bool low_frequency=last_low_us_<0 || now-last_low_us_>=cam_low_frequency_ms*1000LL;
        current_={w.station,gdt};auto cam=encode_cam(w,gdt,low_frequency);
        if(low_frequency)last_low_us_=now;
        need(sent_cam.emplace(current_,std::vector<std::uint8_t>(cam.begin(),cam.end())).second,"duplicate CAM key");
        cam_trace<<"CAM_UPER_TX,"<<id_<<','<<w.station<<','<<gdt<<','<<now<<','<<hex(sent_cam.at(current_))<<'\n';
        packet_row("CAM_UPER_TX",id_,(std::uint64_t(w.station)<<32)|unsigned(gdt),sent_cam.at(current_));
        if(ground_off_cars.count(id_))return;
        v::btp::HeaderB btp;btp.destination_port=v::btp::ports::CAM;btp.destination_port_info=v::host_cast<std::uint16_t>(0);
        v::ByteBuffer h;v::serialize_into_buffer(btp,h);auto packet=std::make_unique<v::DownPacket>();
        (*packet)[v::OsiLayer::Transport]=std::move(h);(*packet)[v::OsiLayer::Application]=std::move(cam);
        v::geonet::ShbDataRequest req(mib_,v::aid::CA);req.upper_protocol=v::geonet::UpperProtocol::BTP_B;req.max_hop_limit=1;
        need(router_.request(req,std::move(packet)).accepted(),"GN rejected CAM");++tx_;
    }
    // `send_denm()` odošle výstrahu DENM cez Vanetza a pozemné ns-3 rádio.
    void send_denm(const DenmEvent& e){
        need(id_==e.source_id&&track_.front().kind=="car","DENM source is not the scheduled car");
        auto it=std::upper_bound(track_.begin(),track_.end(),e.time_us,
            [](std::int64_t t,const Sample& w){return t<w.us;});
        need(it!=track_.begin(),"DENM event precedes car position");
        const auto& w=*std::prev(it);const auto& previous=it-track_.begin()>1?*std::prev(it,2):w;
        auto denm=make_denm(w,previous,e);auto raw=denm.encode();
        need(decode_denm(raw)==denm,"DENM UPER roundtrip changed");
        const auto id=denm_id(denm);packet_row("DENM_UPER_TX",id_,id,raw);
        emit_denm(raw,id,e.radius_m,w);
        if(e.repetition_ms&&e.operation!="cancel"){
            std::int64_t next=tracks.at(id_).back().us+100000;
            for(const auto& future:denm_events)if(future.source_id==e.source_id&&future.sequence==e.sequence&&future.time_us>e.time_us)
                next=std::min(next,future.time_us);
            for(std::int64_t t=e.time_us+e.repetition_ms*1000LL;
                t<next&&t<e.time_us+std::int64_t(e.validity_s)*1000000;t+=e.repetition_ms*1000LL)
                n::Simulator::Schedule(n::MicroSeconds(t-e.time_us),[this,raw,id,radius=e.radius_m,w]{
                    packet_row("DENM_REPEAT_TX",id_,id,raw);emit_denm(raw,id,radius,w);
                });
        }
    }
    void emit_denm(const std::vector<std::uint8_t>& raw,std::uint64_t id,unsigned radius,const Sample& center){
        v::btp::HeaderB btp;btp.destination_port=v::btp::ports::DENM;
        btp.destination_port_info=v::host_cast<std::uint16_t>(0);
        v::ByteBuffer header;v::serialize_into_buffer(btp,header);
        auto packet=std::make_unique<v::DownPacket>();
        (*packet)[v::OsiLayer::Transport]=std::move(header);
        (*packet)[v::OsiLayer::Application]=v::ByteBuffer(raw.begin(),raw.end());
        v::geonet::GbcDataRequest req(mib_,v::aid::DEN);
        req.upper_protocol=v::geonet::UpperProtocol::BTP_B;req.max_hop_limit=3;
        v::geonet::Circle circle;circle.r=double(radius)*v::units::si::meters;
        req.destination.shape=circle;
        req.destination.position=v::geonet::GeodeticPosition(
            (center.lat/1e7)*v::units::degrees,(center.lon/1e7)*v::units::degrees);
        req.destination.angle=v::units::Angle::from_value(0.0);
        need(router_.request(req,std::move(packet)).accepted(),"GN rejected DENM GBC");
        packet_row("CAR_DENM_GBC_TX",id_,id,raw);
    }
    // `request()` prijme požiadavku Vanetza na odoslanie rámca cez ns-3 zariadenie.
    void request(const v::dcc::DataRequest& req,std::unique_ptr<v::ChunkPacket> packet) override {
        need(req.ether_type.host()==0x8947,"unexpected EtherType");v::ByteBuffer wire;
        for(auto layer:v::osi_layer_range<v::OsiLayer::Network,v::OsiLayer::Application>()){
            v::ByteBuffer part;(*packet)[layer].convert(part);wire.insert(wire.end(),part.begin(),part.end());}
        static constexpr std::array<std::uint8_t,4> denm_port{0x07,0xd2,0,0};
        auto pos=std::search(wire.begin(),wire.end(),denm_port.begin(),denm_port.end());
        if(!denm_events.empty()&&pos!=wire.end()){
            std::vector<std::uint8_t> raw(std::next(pos,4),wire.end());
            packet_row("GN_BTP_DENM_TX",id_,denm_id(decode_denm(raw)),wire);
            need(device_->Send(n::Create<n::Packet>(wire.data(),wire.size()),
                n::Mac48Address::GetBroadcast(),0x8947),"DENM OCB Send failed");return;
        }
        need(wire.size()>=80 && wire.size()<=120,"GN packet size outside CAM reference");
        packet_row("GN_BTP_CAM_TX",id_,(std::uint64_t(current_.first)<<32)|unsigned(current_.second),wire);
        cam_trace<<"GN_BTP_CAM_TX,"<<id_<<','<<current_.first<<','<<current_.second<<','
                 <<n::Simulator::Now().GetMicroSeconds()<<','<<hex(wire)<<'\n';
        need(device_->Send(n::Create<n::Packet>(wire.data(),wire.size()),n::Mac48Address::GetBroadcast(),0x8947),"OCB Send failed");
    }
    bool receive(n::Ptr<n::NetDevice>,n::Ptr<const n::Packet> packet,std::uint16_t protocol,const n::Address& from) {
        if(ground_off_cars.count(id_)||ground_off_rsus.count(id_))return false;
        if(protocol!=0x8947)return false;v::ByteBuffer bytes(packet->GetSize());packet->CopyData(bytes.data(),bytes.size());
        pending_=bytes;std::ostringstream s;s<<n::Mac48Address::ConvertFrom(from);v::MacAddress sender;
        need(v::parse_mac_address(s.str(),sender),"source MAC parse failed");
        auto up=std::make_unique<v::UpPacket>(v::CohesivePacket(std::move(bytes),v::OsiLayer::Network));
        router_.indicate(std::move(up),sender,v::cBroadcastMacAddress);return true;
    }
    // `indicate()` prevezme z Vanetza dekódovanú prijatú ITS správu.
    void indicate(const v::btp::DataIndication& indication,std::unique_ptr<v::UpPacket> packet) override {
        if(!denm_events.empty()&&indication.destination_port==v::btp::ports::DENM){
            auto view=boost::create_byte_view(*packet,v::OsiLayer::Session,v::OsiLayer::Application);
            std::vector<std::uint8_t> raw(view.begin(),view.end());auto denm=decode_denm(raw);
            const auto& m=denm->denm.management;const auto id=denm_id(denm);
            long detection=0,reference=0;
            need(asn_INTEGER2long(&m.detectionTime,&detection)==0&&
                 asn_INTEGER2long(&m.referenceTime,&reference)==0,"DENM timestamps unreadable");
            const auto action=std::make_pair(unsigned(m.actionId.originatingStationId),
                unsigned(m.actionId.sequenceNumber));
            if(track_.front().kind=="rsu"&&cars_only.count(station_owner.at(action.first)))return;
            const auto seen=denm_seen_.find(action);
            const auto now=its_ms(n::Simulator::Now().GetMicroSeconds());
            const long validity=m.validityDuration?*m.validityDuration:600;
            const char* reject=track_.front().station==m.actionId.originatingStationId?"own_action":
                now>detection+validity*1000?"expired":
                m.termination&&seen==denm_seen_.end()?"unknown_termination":
                seen!=denm_seen_.end()&&reference<=seen->second?
                    (reference==seen->second?"duplicate":"outdated"):nullptr;
            if(reject){packet_trace<<"DENM_REJECTED,"<<id_<<','<<std::hex<<std::setw(16)<<std::setfill('0')
                 <<id<<std::dec<<','<<n::Simulator::Now().GetMicroSeconds()<<",0,\n";return;}
            denm_seen_[action]=reference;packet_row("DENM_UPER_RX",id_,id,raw);return;
        }
        need(indication.destination_port==v::btp::ports::CAM,"BTP port mismatch");
        auto view=boost::create_byte_view(*packet,v::OsiLayer::Session,v::OsiLayer::Application);
        std::vector<std::uint8_t> bytes(view.begin(),view.end());v::asn1::PacketVisitor<v::asn1::r2::Cam> visitor;
        auto decoded=boost::apply_visitor(visitor,*packet);need(decoded && decoded->validate(),"CAM decode failed");
        auto key=std::make_pair(unsigned(decoded->content()->header.stationId),long(decoded->content()->cam.generationDeltaTime));
        need(sent_cam.count(key) && sent_cam.at(key)==bytes,"CAM bytes differ from sent packet");
        if(tracks.at(id_).front().kind=="rsu"&&cars_only.count(station_owner.at(key.first)))return;
        ++rx_;rx_trace<<id_<<','<<key.first<<','<<key.second<<','<<n::Simulator::Now().GetMicroSeconds()<<','
                      <<hex(bytes)<<','<<hex(pending_)<<'\n';
        packet_row("CAM_UPER_RX",id_,(std::uint64_t(key.first)<<32)|unsigned(key.second),bytes);
    }
    unsigned tx()const{return tx_;} unsigned rx()const{return rx_;} unsigned gn_drops()const{return gn_drops_;}
private:
    n::Ptr<n::NetDevice> device_;std::string id_;const std::vector<Sample>& track_;bool dcc_;DccPolicy policy_;
    v::MacAddress mac_;Runtime runtime_;v::geonet::MIB mib_;v::geonet::Router router_;v::btp::PortDispatcher dispatcher_;
    std::vector<Interval> busy_;std::unique_ptr<Sample> last_;std::pair<unsigned,long> current_{};
    v::ByteBuffer pending_;unsigned tx_=0,rx_=0,gn_drops_=0;
    std::int64_t tgen_ms_=cam_tgen_max_ms,last_low_us_=-1;unsigned periodic_count_=0;
    std::map<std::pair<unsigned,unsigned>,long> denm_seen_;
};
// Zostaví pozemné ns-3 uzly a OCB kanál podľa vstupných waypointov, parametrov rádia a budov.
// Rozvrhne časové vzorky a po Simulator::Run zapíše raw stopy pre nezávislý verifier.
int main(int argc,char** argv){
    try{
        std::string waypoints,output,mode="urban_los",buildings,osm_buildings,denm_events_file,rsu_radio_config,car_radio_config;bool dcc=false,shadowing=false;
        unsigned seed=314159,run=1,phase_us=0,mid_ms=250,high_ms=500,rate_mbps=6,channel_number=180;
        double power=20,noise=7,tx_gain_dbi=0,rx_gain_dbi=0,low_cbr=0.004,high_cbr=0.012;
        n::CommandLine cmd(__FILE__);cmd.AddValue("waypoints","100ms FCD-derived waypoints",waypoints);
        cmd.AddValue("output","existing raw output directory",output);cmd.AddValue("radio_mode","friis|urban_los|urban_nlos",mode);
        cmd.AddValue("buildings","validated axis-aligned building-box CSV",buildings);
        cmd.AddValue("osm_buildings","pinned OSM polygon and selected-height CSV",osm_buildings);
        cmd.AddValue("rsu_radio_config","per-RSU PHY and antenna CSV",rsu_radio_config);
        cmd.AddValue("car_radio_config","per-car PHY and antenna CSV",car_radio_config);
        cmd.AddValue("shadowing","3GPP shadowing sensitivity",shadowing);
        cmd.AddValue("dcc","hypothetical measured-CBR feedback",dcc);cmd.AddValue("seed","ns-3 seed",seed);
        cmd.AddValue("run","ns-3 run",run);cmd.AddValue("phase_us","per-station CAM check phase in microseconds",phase_us);
        cmd.AddValue("dcc_low_cbr","research CBR lower threshold",low_cbr);
        cmd.AddValue("dcc_high_cbr","research CBR upper threshold",high_cbr);
        cmd.AddValue("dcc_mid_ms","research intermediate minimum CAM interval",mid_ms);
        cmd.AddValue("dcc_high_ms","research high-load minimum CAM interval",high_ms);
        cmd.AddValue("cam_distance_m","CAM movement trigger distance",cam_distance_m);
        cmd.AddValue("cam_speed_mps","CAM movement trigger speed difference",cam_speed_mps);
        cmd.AddValue("cam_heading_deg","CAM movement trigger heading difference",cam_heading_deg);
        cmd.AddValue("cam_low_frequency_ms","CAM low-frequency container interval",cam_low_frequency_ms);
        cmd.AddValue("cam_tgen_max_ms","CAM maximum generation interval",cam_tgen_max_ms);
        cmd.AddValue("cam_periodic_repeat","CAM periodic repeats before reset",cam_periodic_repeat);
        cmd.AddValue("car_antenna_height_m","car ground antenna height",car_antenna_height_m);
        cmd.AddValue("rsu_antenna_min_height_m","minimum RSU ground antenna height",rsu_antenna_min_height_m);
        cmd.AddValue("rsu_roof_clearance_m","RSU antenna offset above roof",rsu_roof_clearance_m);
        cmd.AddValue("tx_power_dbm","OCB TX power",power);
        cmd.AddValue("noise_figure_db","OCB RX noise figure",noise);
        cmd.AddValue("rate_mbps","10 MHz OCB PHY rate: 3, 6, 12 or 24 Mbps",rate_mbps);
        cmd.AddValue("channel_number","10 MHz OCB channel: 172..184, even numbers",channel_number);
        cmd.AddValue("tx_gain_dbi","OCB TX antenna gain",tx_gain_dbi);
        cmd.AddValue("rx_gain_dbi","OCB RX antenna gain",rx_gain_dbi);
        cmd.AddValue("denm_events","explicit traffic-jam event CSV",denm_events_file);
        cmd.AddValue("utcOrigin","UTC start of the shared scenario clock",runtime_origin);
        cmd.Parse(argc,argv);
        need(runtime_origin.size()==19&&(runtime_origin[10]=='T'||runtime_origin[10]==' '),
             "UTC origin must use YYYY-MM-DDTHH:MM:SS");
        runtime_origin[10]=' ';
        need(!waypoints.empty()&&!output.empty(),"waypoints and output required");
        need(mode=="friis"||mode=="urban_los"||mode=="urban_nlos"||mode=="urban_building"||mode=="urban_osm_building","unsupported radio mode");
        building_mode=mode=="urban_building";
        need((building_mode&&!buildings.empty())||(!building_mode&&buildings.empty()),"building input/mode mismatch");
        need((mode=="urban_osm_building"&&!osm_buildings.empty())||
             (mode!="urban_osm_building"&&osm_buildings.empty()),"OSM building input/mode mismatch");
        if(building_mode)load_boxes(buildings);
        need(mode!="friis"||!shadowing,"Friis shadowing unsupported");
        need(std::isfinite(low_cbr)&&std::isfinite(high_cbr)&&0<=low_cbr&&low_cbr<high_cbr&&high_cbr<=1&&
             100<=mid_ms&&mid_ms<=high_ms&&high_ms<=1000,"DCC research policy invalid");
        need(power>=0&&power<=33&&noise>=0&&noise<=20&&phase_us<=1000&&
             cam_distance_m>=0&&cam_distance_m<=100&&cam_speed_mps>=0&&cam_speed_mps<=20&&
             cam_heading_deg>=0&&cam_heading_deg<=180&&
             cam_low_frequency_ms>=100&&cam_low_frequency_ms<=cam_tgen_max_ms&&cam_tgen_max_ms<=1000&&
             cam_periodic_repeat>=1&&cam_periodic_repeat<=20&&
             car_antenna_height_m>=0.2&&car_antenna_height_m<=10&&
             rsu_antenna_min_height_m>=0.2&&rsu_antenna_min_height_m<=100&&
             rsu_roof_clearance_m>=0&&rsu_roof_clearance_m<=50&&
             (rate_mbps==3||rate_mbps==6||rate_mbps==12||rate_mbps==24)&&
             channel_number>=172&&channel_number<=184&&channel_number%2==0&&
             std::isfinite(tx_gain_dbi)&&std::isfinite(rx_gain_dbi)&&
             tx_gain_dbi>=-20&&tx_gain_dbi<=20&&rx_gain_dbi>=-20&&rx_gain_dbi<=20,
             "radio or phase parameter out of bounds");load(waypoints);
        // Súbor s profilmi RSU sa číta po vzorkách polohy a pred inštaláciou rádia. ID musia
        // presne zodpovedať uzlom; PHY potom dostane parametre svojho RSU.
        rsuradio::load(rsu_radio_config);
        // Pozemný engine načíta profil každého auta a kontroluje vlastníka podľa stopy polôh. PHY
        // atribúty a výška antény sa používajú na konkrétnom uzle, nie iba pri exporte formulára.
        rsuradio::load_cars(car_radio_config);
        for(const auto& pair:rsuradio::profiles)need(tracks.count(pair.first)&&tracks.at(pair.first).front().kind=="rsu","RSU radio owner invalid");
        if(!rsu_radio_config.empty())for(const auto& id:order)if(tracks.at(id).front().kind=="rsu")need(rsuradio::find(id)!=nullptr,"RSU radio profile absent");
        for(const auto& pair:rsuradio::car_profiles)need(tracks.count(pair.first)&&tracks.at(pair.first).front().kind=="car","car radio owner invalid");
        if(!car_radio_config.empty())for(const auto& id:order)if(tracks.at(id).front().kind=="car")need(rsuradio::find_car(id)!=nullptr,"car radio profile absent");
        if(!denm_events_file.empty()){
            std::ifstream input(denm_events_file);need(bool(input),"DENM event CSV missing");
            std::string line;std::getline(input,line);
            need(line=="time_us,source_id,sequence,operation,validity_s,radius_m,repetition_ms","DENM CSV header invalid");
            std::set<std::pair<std::string,unsigned>> actions;std::int64_t previous=-1;
            while(std::getline(input,line)){
                if(line.empty())continue;std::stringstream ss(line);std::vector<std::string> cells;std::string cell;
                while(std::getline(ss,cell,','))cells.push_back(cell);need(cells.size()==7,"DENM CSV row invalid");
                DenmEvent e{std::stoll(cells[0]),cells[1],unsigned(std::stoul(cells[2])),cells[3],
                    unsigned(std::stoul(cells[4])),unsigned(std::stoul(cells[5])),unsigned(std::stoul(cells[6]))};
                need(tracks.count(e.source_id)&&tracks.at(e.source_id).front().kind=="car"&&
                     e.time_us>=previous&&e.time_us>=tracks.at(e.source_id).front().us&&
                     e.time_us<tracks.at(e.source_id).back().us+100000&&e.sequence<=65535&&
                     e.validity_s>=1&&e.validity_s<=86400&&e.radius_m>=1&&e.radius_m<=1780&&
                     (e.repetition_ms==0||(e.repetition_ms>=100&&e.repetition_ms<=60000))&&
                     (e.operation=="new"?actions.insert({e.source_id,e.sequence}).second:
                       (e.operation=="update"||e.operation=="cancel")&&actions.count({e.source_id,e.sequence})),
                     "DENM lifecycle or time invalid");
                denm_events.push_back(e);previous=e.time_us;
            }
            need(!denm_events.empty(),"DENM event CSV empty");
        }
        ground_off_cars=policy_ids("SIM_GROUND_OFF_CARS","car");
        cars_only=policy_ids("SIM_CARS_ONLY","car");
        ground_off_rsus=policy_ids("SIM_GROUND_OFF_RSUS","rsu");
        need(std::none_of(ground_off_cars.begin(),ground_off_cars.end(),[](const auto& id){return cars_only.count(id);}),"car ground policy overlap");
        cam_trace.open(output+"/cam.csv");phy_trace.open(output+"/phy_state.csv");
        packet_trace.open(output+"/trace.csv");
        phy_drop_trace.open(output+"/phy_drop.csv");
        decision_trace.open(output+"/dcc_decisions.csv");rx_trace.open(output+"/rx.csv");
        if(building_mode)building_trace.open(output+"/building_los.csv");
        need(bool(cam_trace)&&bool(packet_trace)&&bool(phy_trace)&&bool(decision_trace)&&bool(rx_trace)&&bool(phy_drop_trace),"trace open failed");
        packet_trace<<"stage,node_id,event_id,time_us,bytes,raw_hex\n";
        if(building_mode)need(bool(building_trace),"building trace open failed");
        cam_trace<<"stage,node_id,station_id,gdt_ms,time_us,raw_hex\n";
        phy_trace<<"node_id,start_us,end_us,state,observed_us,seq\n";
        phy_drop_trace<<"node_id,time_us,reason\n";
        decision_trace<<"node_id,time_us,seq,cbr_1s,dcc_min_ms,t_gen_cam_ms,motion_trigger,periodic_trigger,trigger_condition,send,distance_m,speed_delta_mps,heading_delta_deg\n";
        rx_trace<<"rx_node_id,station_id,gdt_ms,time_us,cam_hex,gn_hex\n";
        if(building_mode)building_trace<<"time_us,node_id,rsu_id,blocked\n";
        n::RngSeedManager::SetSeed(seed);n::RngSeedManager::SetRun(run);
        n::NodeContainer nodes;nodes.Create(order.size());n::MobilityHelper mobility;
        auto positions=n::CreateObject<n::ListPositionAllocator>();
        for(const auto& id:order){const auto& w=tracks.at(id).front();positions->Add(n::Vector(w.x,w.y,radio_height(w)));}
        mobility.SetPositionAllocator(positions);mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");mobility.Install(nodes);
        if(building_mode){
            for(const auto& b:boxes){auto object=n::CreateObject<n::Building>();
                object->SetBoundaries(n::Box(b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax));}
            n::BuildingsHelper::Install(nodes);
        }
        const std::string rate="OfdmRate"+std::to_string(rate_mbps)+"MbpsBW10MHz";
        const double frequency_hz=(5000+5*channel_number)*1e6;
        n::Config::SetDefault("ns3::WifiRemoteStationManager::NonUnicastMode",n::StringValue(rate));
        n::Wifi80211pHelper wifi=n::Wifi80211pHelper::Default();
        wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager","DataMode",n::StringValue(rate),"ControlMode",n::StringValue(rate));
        n::YansWifiPhyHelper phy;
        if(mode=="friis"){
            n::YansWifiChannelHelper channel;channel.SetPropagationDelay("ns3::ConstantSpeedPropagationDelayModel");
            channel.AddPropagationLoss("ns3::FriisPropagationLossModel","Frequency",n::DoubleValue(frequency_hz));phy.SetChannel(channel.Create());
        }else{
            n::Ptr<n::ChannelConditionModel> condition;
            if(mode=="urban_los")condition=n::CreateObject<n::AlwaysLosChannelConditionModel>();
            else if(mode=="urban_nlos")condition=n::CreateObject<n::NeverLosChannelConditionModel>();
            else if(mode=="urban_osm_building"){
                osm_condition=n::CreateObject<groundradio::OSMBuildingCondition>();
                osm_condition->Load(osm_buildings);condition=osm_condition;
            }else condition=n::CreateObject<n::ThreeGppV2vUrbanChannelConditionModel>();
            condition->AssignStreams(5);
            auto loss=n::CreateObject<n::ThreeGppV2vUrbanPropagationLossModel>();
            loss->SetAttribute("Frequency",n::DoubleValue(frequency_hz));loss->SetAttribute("ShadowingEnabled",n::BooleanValue(shadowing));
            loss->SetAttribute("BuildingPenetrationLossesEnabled",n::BooleanValue(false));
            loss->SetAttribute("ChannelConditionModel",n::PointerValue(condition));
            loss->AssignStreams(10);
            auto channel=n::CreateObject<n::YansWifiChannel>();channel->SetPropagationLossModel(loss);
            channel->SetPropagationDelayModel(n::CreateObject<n::ConstantSpeedPropagationDelayModel>());phy.SetChannel(channel);
        }
        phy.Set("ChannelSettings",n::StringValue("{"+std::to_string(channel_number)+", 10, BAND_5GHZ, 0}"));
        phy.Set("TxPowerStart",n::DoubleValue(power));phy.Set("TxPowerEnd",n::DoubleValue(power));
        phy.Set("TxGain",n::DoubleValue(tx_gain_dbi));phy.Set("RxGain",n::DoubleValue(rx_gain_dbi));
        phy.Set("RxNoiseFigure",n::DoubleValue(noise));phy.SetPcapDataLinkType(n::WifiPhyHelper::DLT_IEEE802_11);
        std::cout << "OCB_CONFIG RATE_MBPS=" << rate_mbps << " CHANNEL=" << channel_number
                  << " FREQUENCY_HZ=" << std::fixed << std::setprecision(0) << frequency_hz << std::defaultfloat
                  << " TX_GAIN_DBI=" << tx_gain_dbi
                  << " RX_GAIN_DBI=" << rx_gain_dbi << " SHADOWING=" << shadowing << '\n';
        auto mac=n::QosWaveMacHelper::Default();auto devices=wifi.Install(phy,mac,nodes);
        phy.EnablePcap(output+"/ocb",devices);
        std::vector<std::unique_ptr<Station>> stations;
        for(size_t i=0;i<order.size();++i){
            auto dev=n::DynamicCast<n::WifiNetDevice>(devices.Get(i));need(dev && n::DynamicCast<n::OcbWifiMac>(dev->GetMac()),"not OCB");
            const bool car=tracks.at(order[i]).front().kind=="car";
            if(const auto* profile=car?rsuradio::find_car(order[i]):rsuradio::find(order[i])){
                dev->GetPhy()->SetAttribute("TxPowerStart",n::DoubleValue(profile->power));
                dev->GetPhy()->SetAttribute("TxPowerEnd",n::DoubleValue(profile->power));
                dev->GetPhy()->SetAttribute("RxNoiseFigure",n::DoubleValue(profile->noise));
                dev->GetPhy()->SetAttribute("TxGain",n::DoubleValue(profile->tx_gain));
                dev->GetPhy()->SetAttribute("RxGain",n::DoubleValue(profile->rx_gain));
                std::cout<<std::setprecision(12)<<(car?"CAR_RADIO_PROFILE ID=":"RSU_RADIO_PROFILE ID=")<<order[i]<<" TX="<<profile->power
                         <<" NOISE="<<profile->noise<<" TX_GAIN="<<profile->tx_gain
                         <<" RX_GAIN="<<profile->rx_gain<<" HEIGHT="<<profile->height<<'\n'<<std::setprecision(6);
            }
            need(dev->GetPhy()->GetChannelWidth()==10&&
                 dev->GetPhy()->GetChannelNumber()==channel_number&&
                 dev->GetPhy()->GetFrequency()==5000+5*channel_number,"channel mismatch");
            stations.emplace_back(std::make_unique<Station>(dev,order[i],tracks.at(order[i]),dcc,
                                                    DccPolicy{low_cbr,high_cbr,mid_ms,high_ms}));
            need(dev->GetPhy()->GetState()->TraceConnectWithoutContext("State",n::MakeCallback(&Station::on_state,stations.back().get())),"PHY state trace absent");
            need(dev->GetPhy()->TraceConnectWithoutContext("PhyRxDrop",n::MakeCallback(&Station::on_drop,stations.back().get())),"PHY drop trace absent");
        }
        const auto count=tracks.at(order.front()).size();
        for(size_t j=0;j<count;++j){
            for(size_t i=0;i<order.size();++i){auto w=tracks.at(order[i])[j];auto s=stations[i].get();
                n::Simulator::Schedule(n::MicroSeconds(w.us),[s,w]{s->update(w);});}
            if(building_mode){
                auto when=tracks.at(order.front())[j].us;
                n::Simulator::Schedule(n::MicroSeconds(when),[&nodes,when]{
                    auto model=n::CreateObject<n::BuildingsChannelConditionModel>();
                    for(size_t i=0;i<order.size();++i)if(tracks.at(order[i]).front().kind=="car")
                        for(size_t k=0;k<order.size();++k)if(tracks.at(order[k]).front().kind=="rsu"){
                            auto a=nodes.Get(i)->GetObject<n::MobilityModel>();
                            auto b=nodes.Get(k)->GetObject<n::MobilityModel>();
                            auto condition=model->GetChannelCondition(a,b);
                            building_trace<<when<<','<<order[i]<<','<<order[k]<<','<<int(condition->IsNlos())<<'\n';
                        }
                });
            }
            for(size_t i=0;i<order.size();++i)if(tracks.at(order[i])[j].kind=="car"){
                auto w=tracks.at(order[i])[j];auto s=stations[i].get();
                n::Simulator::Schedule(n::MicroSeconds(w.us+phase_us*(i+1)),[s,w]{s->check(w);});
            }
        }
        if(!denm_events.empty()){
            for(const auto& e:denm_events){
                auto found=std::find(order.begin(),order.end(),e.source_id);
                auto source=stations.at(found-order.begin()).get();
                n::Simulator::Schedule(n::MicroSeconds(e.time_us),[source,e]{source->send_denm(e);});
            }
        }
        auto stop_us=tracks.at(order.front()).back().us+1000000;
        if(const char* exact=std::getenv("SIM_LOGICAL_END_US")){
            stop_us=std::stoll(exact);
            need(stop_us==tracks.at(order.front()).back().us+100000,
                 "logical experiment end must follow the final CAM tick by 100 ms");
        }
        n::Simulator::Stop(n::MicroSeconds(stop_us));n::Simulator::Run();
        unsigned total=0,received=0,drops=0;for(auto& s:stations){total+=s->tx();received+=s->rx();drops+=s->gn_drops();}
        std::cout<<"GROUND_NODES="<<order.size()<<" CAM_TX="<<total<<" CAM_RX="<<received
                 <<" PHY_DROPS="<<phy_drops<<" GN_DROPS="<<drops<<" DCC="<<dcc<<" RADIO="<<mode
                 <<" SHADOWING="<<shadowing<<" TX_POWER_DBM="<<std::setprecision(12)<<power
                 <<" RX_NOISE_FIGURE_DB="<<noise<<" PHASE_US="<<phase_us
                 <<" SEED="<<seed<<" RUN="<<run<<" DCC_LOW_CBR="<<low_cbr
                 <<" DCC_HIGH_CBR="<<high_cbr<<" DCC_MID_MS="<<mid_ms
                 <<" DCC_HIGH_MS="<<high_ms<<'\n';
        n::Simulator::Destroy();return 0;
    }catch(const std::exception& e){std::cerr<<"GROUND_ERROR="<<e.what()<<'\n';return 2;}
}
