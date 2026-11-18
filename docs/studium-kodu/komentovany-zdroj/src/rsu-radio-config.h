// Načíta presný CSV profil každej RSU pre pozemnú 802.11p PHY v oboch natívnych enginoch.
// Nepovolené rozsahy a cudzie ID zastavia beh pred vysielaním.
#pragma once

#include <cmath>
#include <fstream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace rsuradio {
struct Profile {
    double power, noise, tx_gain, rx_gain, height;
};
inline std::map<std::string, Profile> profiles;
inline std::map<std::string, Profile> car_profiles;

// Spoločný čítač kontroluje samostatné CSV áut a RSU. Zachová rozdielne rozsahy výšky antény a
// odmieta duplicitné ID, aby profil nebol priradený inému uzlu.
inline void load_into(const std::string& path, std::map<std::string, Profile>& destination,
                      const std::string& kind, double max_height) {
    destination.clear();
    if (path.empty()) return;
    std::ifstream file(path);
    if (!file) throw std::runtime_error(kind + " radio CSV missing: " + path);
    std::string line;
    std::getline(file, line);
    if (line != "id,tx_power_dbm,noise_figure_db,tx_gain_dbi,rx_gain_dbi,antenna_height_m")
        throw std::runtime_error(kind + " radio CSV header invalid");
    while (std::getline(file, line)) {
        if (line.empty()) continue;
        std::stringstream stream(line);
        std::vector<std::string> cells;
        std::string cell;
        while (std::getline(stream, cell, ',')) cells.push_back(cell);
        if (cells.size() != 6) throw std::runtime_error(kind + " radio CSV row invalid");
        Profile p{std::stod(cells[1]), std::stod(cells[2]), std::stod(cells[3]),
                  std::stod(cells[4]), std::stod(cells[5])};
        if (!std::isfinite(p.power) || p.power < 0 || p.power > 33 ||
            !std::isfinite(p.noise) || p.noise < 0 || p.noise > 20 ||
            !std::isfinite(p.tx_gain) || p.tx_gain < -20 || p.tx_gain > 20 ||
            !std::isfinite(p.rx_gain) || p.rx_gain < -20 || p.rx_gain > 20 ||
            !std::isfinite(p.height) || (p.height != -1 && (p.height < 0.2 || p.height > max_height)) ||
            !destination.emplace(cells[0], p).second)
            throw std::runtime_error(kind + " radio CSV value or ID invalid");
    }
}
// Spoločný parser odmieta neplatné polia a duplicity; výška −1 znamená odvodenie od strechy a
// spoločného minima, nie negatívnu fyzickú výšku.
inline void load(const std::string& path) { load_into(path, profiles, "RSU", 100); }
// `load_cars()` načíta dáta zo súboru alebo pamäte.
inline void load_cars(const std::string& path) { load_into(path, car_profiles, "car", 10); }
inline const Profile* find(const std::string& id) {
    const auto it = profiles.find(id);
    return it == profiles.end() ? nullptr : &it->second;
}
inline const Profile* find_car(const std::string& id) {
    const auto it = car_profiles.find(id);
    return it == car_profiles.end() ? nullptr : &it->second;
}
} // namespace rsuradio
