// Scenario physical conditions evaluated at the native SNS-3 user channel.
// The modem remains generic DVB; mounting, compensation and slew are declared
// sensitivity inputs, not measurements of an operator terminal.
#ifndef SIM_NATIVE_SATELLITE_CONDITION_H
#define SIM_NATIVE_SATELLITE_CONDITION_H

#include "ground-building-condition.h"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace satelliteradio {

inline ns3::Vector add(ns3::Vector a, ns3::Vector b) { return {a.x+b.x,a.y+b.y,a.z+b.z}; }
inline ns3::Vector sub(ns3::Vector a, ns3::Vector b) { return {a.x-b.x,a.y-b.y,a.z-b.z}; }
inline ns3::Vector mul(ns3::Vector a, double k) { return {a.x*k,a.y*k,a.z*k}; }
inline double dot(ns3::Vector a, ns3::Vector b) { return a.x*b.x+a.y*b.y+a.z*b.z; }
inline ns3::Vector unit(ns3::Vector a) {
    const double length=std::sqrt(dot(a,a));
    if (!(length>0)) throw std::runtime_error("satellite sight vector invalid");
    return mul(a,1/length);
}
inline double angle(ns3::Vector a, ns3::Vector b) {
    return std::acos(std::clamp(dot(unit(a),unit(b)),-1.0,1.0))*180.0/M_PI;
}
inline ns3::Vector steer(ns3::Vector from, ns3::Vector toward, double maximum_deg) {
    const double separation=angle(from,toward);
    if (separation<=maximum_deg) return unit(toward);
    if (maximum_deg<=0) return unit(from);
    const auto start=unit(from),target=unit(toward);
    auto tangent=sub(target,mul(start,dot(start,target)));
    if (dot(tangent,tangent)<1e-18)
        tangent=std::abs(start.z)<.9 ? ns3::Vector{-start.y,start.x,0} :
                                       ns3::Vector{0,-start.z,start.y};
    const double step=maximum_deg*M_PI/180;
    return unit(add(mul(start,std::cos(step)),mul(unit(tangent),std::sin(step))));
}

struct Profile {
    std::string owner;
    double tilt_deg=0, azimuth_deg=0, half_fov_deg=180;
    double rf_hz=1.0e9, compensation=1, tolerance_hz=1.0e12;
    double zenith_cone_deg=180, steering_rate_deg_s=360, beam_half_angle_deg=180;
    double x_m=0,y_m=0,z_m=5;
    ns3::Vector normal,aim;
    std::int64_t last_us=0;
    unsigned serving_sat=0;
};

class Condition {
public:
    explicit Condition(const std::string& file, const std::string& trace_path,
                       ns3::Ptr<groundradio::OSMBuildingCondition> buildings)
        : buildings_(buildings), trace_(trace_path) {
        if (!trace_) throw std::runtime_error("satellite RF trace cannot open");
        trace_ << "time_us,rsu_id,sat_id,channel,carrier_hz,reason,off_axis_deg,pointing_error_deg,range_rate_mps,doppler_hz,residual_hz,building_blocked\n";
        std::ifstream in(file);
        if (!in) throw std::runtime_error("satellite terminal profile missing");
        std::string line;
        std::getline(in,line);
        if (line!="rsu_id,tilt_deg,azimuth_deg,half_fov_deg,rf_hz,compensation,doppler_tolerance_hz,zenith_cone_deg,steering_rate_deg_s,beam_half_angle_deg")
            throw std::runtime_error("satellite terminal profile header invalid");
        while (std::getline(in,line)) {
            if (line.empty()) continue;
            std::stringstream stream(line); std::vector<std::string> cells; std::string cell;
            while (std::getline(stream,cell,',')) cells.push_back(cell);
            if (cells.size()!=10) throw std::runtime_error("satellite terminal profile row invalid");
            Profile p;
            p.owner=cells[0];
            p.tilt_deg=std::stod(cells[1]); p.azimuth_deg=std::stod(cells[2]);
            p.half_fov_deg=std::stod(cells[3]); p.rf_hz=std::stod(cells[4]);
            p.compensation=std::stod(cells[5]); p.tolerance_hz=std::stod(cells[6]);
            p.zenith_cone_deg=std::stod(cells[7]); p.steering_rate_deg_s=std::stod(cells[8]);
            p.beam_half_angle_deg=std::stod(cells[9]);
            if (p.owner.empty() || !std::isfinite(p.rf_hz) || p.rf_hz<=0 ||
                !std::isfinite(p.tilt_deg) || p.tilt_deg<0 || p.tilt_deg>180 ||
                !std::isfinite(p.azimuth_deg) || p.azimuth_deg<0 || p.azimuth_deg>=360 ||
                !std::isfinite(p.half_fov_deg) || p.half_fov_deg<0 || p.half_fov_deg>180 ||
                !std::isfinite(p.compensation) || p.compensation<0 || p.compensation>1 ||
                !std::isfinite(p.tolerance_hz) || p.tolerance_hz<0 ||
                !std::isfinite(p.zenith_cone_deg) || p.zenith_cone_deg<0 || p.zenith_cone_deg>180 ||
                !std::isfinite(p.steering_rate_deg_s) || p.steering_rate_deg_s<0 ||
                !std::isfinite(p.beam_half_angle_deg) || p.beam_half_angle_deg<0 ||
                p.beam_half_angle_deg>180 || !profiles_.emplace(p.owner,p).second)
                throw std::runtime_error("satellite terminal profile value invalid");
        }
        if (profiles_.empty()) throw std::runtime_error("satellite terminal profile empty");
    }

    void Register(const std::string& owner, ns3::Ptr<ns3::MobilityModel> mobility,
                  double lat_deg,double lon_deg,double x_m,double y_m,double mount_height_m,unsigned serving_sat) {
        auto found=profiles_.find(owner);
        if (found==profiles_.end() || !mobility) throw std::runtime_error("satellite terminal registration incomplete");
        auto& p=found->second;
        p.x_m=x_m; p.y_m=y_m; p.z_m=mount_height_m;
        p.serving_sat=serving_sat;
        const double lat=lat_deg*M_PI/180,lon=lon_deg*M_PI/180;
        ns3::Vector east{-std::sin(lon),std::cos(lon),0};
        ns3::Vector north{-std::sin(lat)*std::cos(lon),-std::sin(lat)*std::sin(lon),std::cos(lat)};
        ns3::Vector up{std::cos(lat)*std::cos(lon),std::cos(lat)*std::sin(lon),std::sin(lat)};
        const double tilt=p.tilt_deg*M_PI/180,az=p.azimuth_deg*M_PI/180;
        p.normal=unit(add(mul(up,std::cos(tilt)),mul(add(mul(east,std::sin(az)),mul(north,std::cos(az))),std::sin(tilt))));
        p.aim=p.normal;
        by_mobility_.emplace(ns3::PeekPointer(mobility),owner);
    }

    void RegisterSatellite(unsigned index,ns3::Ptr<ns3::MobilityModel> mobility) {
        satellite_ids_.emplace(ns3::PeekPointer(mobility),index);
    }

    void SetServing(const std::string& owner,unsigned sat) { profiles_.at(owner).serving_sat=sat; }

    bool Accept(ns3::Ptr<ns3::MobilityModel> ground,ns3::Ptr<ns3::MobilityModel> satellite,
                ns3::SatEnums::ChannelType_t channel,double carrier_hz) {
        auto owner=by_mobility_.find(ns3::PeekPointer(ground));
        if (owner==by_mobility_.end())
            throw std::runtime_error("unregistered SNS-3 user-link terminal");
        auto& p=profiles_.at(owner->second);
        const auto sat_id=satellite_ids_.find(ns3::PeekPointer(satellite));
        if (sat_id==satellite_ids_.end()) throw std::runtime_error("satellite RF source unregistered");
        const auto sight=sub(satellite->GetPosition(),ground->GetPosition());
        const auto direction=unit(sight);
        const double off_axis=angle(p.normal,direction);
        const auto now=ns3::Simulator::Now().GetMicroSeconds();
        const double maximum=std::min(p.zenith_cone_deg,p.half_fov_deg);
        auto desired=steer(p.normal,direction,maximum);
        if (sat_id->second==p.serving_sat) {
            p.aim=steer(p.aim,desired,p.steering_rate_deg_s*(now-p.last_us)/1e6);
            p.last_us=now;
        }
        const double pointing=angle(p.aim,direction);
        const double radial=dot(sub(satellite->GetVelocity(),ground->GetVelocity()),direction);
        if (!std::isfinite(carrier_hz) || carrier_hz<=0)
            throw std::runtime_error("native SNS-3 user carrier frequency invalid");
        const double doppler=-carrier_hz*radial/299792458.0;
        const double residual=std::abs(doppler)*(1-p.compensation);
        const double lat=std::asin(std::clamp(ground->GetPosition().z/
            std::sqrt(dot(ground->GetPosition(),ground->GetPosition())),-1.0,1.0));
        const double lon=std::atan2(ground->GetPosition().y,ground->GetPosition().x);
        const double east=-direction.x*std::sin(lon)+direction.y*std::cos(lon);
        const double north=-direction.x*std::sin(lat)*std::cos(lon)-direction.y*std::sin(lat)*std::sin(lon)+direction.z*std::cos(lat);
        const double up=direction.x*std::cos(lat)*std::cos(lon)+direction.y*std::cos(lat)*std::sin(lon)+direction.z*std::sin(lat);
        const double length=up>0 ? std::min(4500.0,500.0/up) : 4500.0;
        const ns3::Vector start{p.x_m,p.y_m,p.z_m};
        const ns3::Vector finish{p.x_m+east*length,p.y_m+north*length,p.z_m+up*length};
        const bool blocked=buildings_ && buildings_->Blocked(start,finish);
        const char* reason=blocked ? "building" : off_axis>p.half_fov_deg+1e-9 ? "mount_fov" :
                           residual>p.tolerance_hz+1e-9 ? "doppler" :
                           pointing>p.beam_half_angle_deg+1e-9 ? "pointing" : "accepted";
        trace_ << now << ',' << p.owner << ',' << sat_id->second << ','
               << (channel==ns3::SatEnums::RETURN_USER_CH ? "return_user" : "forward_user")
               << ',' << std::setprecision(12) << carrier_hz << ',' << reason << ','
               << std::setprecision(10) << off_axis << ','
               << pointing << ',' << radial << ',' << doppler << ',' << residual << ',' << int(blocked) << '\n';
        return reason[0]=='a';
    }

    unsigned Registered() const { return by_mobility_.size(); }

private:
    std::map<std::string,Profile> profiles_;
    std::map<const ns3::MobilityModel*,std::string> by_mobility_;
    std::map<const ns3::MobilityModel*,unsigned> satellite_ids_;
    ns3::Ptr<groundradio::OSMBuildingCondition> buildings_;
    std::ofstream trace_;
};

} // namespace satelliteradio
#endif
