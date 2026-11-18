// Pozemné tienenie budov medzi vysielačom a prijímačom. Na základe geometrie budov rozhoduje o
// dodatočnom útlme alebo blokovaní v rádiovom modeli.
// Deterministic outdoor LOS/NLOS from pinned OSM building footprints.
// Heights are scenario estimates; this is a geometric condition, not a
// calibrated penetration, diffraction, vehicle-body or fading model.
#ifndef SIM_OSM_GROUND_CONDITION_H
#define SIM_OSM_GROUND_CONDITION_H

#include <ns3/propagation-module.h>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace groundradio {

struct Point { double x, y; };
struct Building {
    std::string id;
    double height, xmin, xmax, ymin, ymax;
    std::vector<Point> polygon;
};

// Geometria budov zasahuje priamo do pozemného ns-3 rádiového modelu. Oddeľuje priame spojenie od
// spojenia cez polygón budovy; pri reálnej mape výška môže pochádzať z OSM alebo z deklarovaného
// odhadu.
class OSMBuildingCondition final : public ns3::ChannelConditionModel {
public:
    static ns3::TypeId GetTypeId() {
        static ns3::TypeId id = ns3::TypeId("bp::GroundBuildingCondition")
            .SetParent<ns3::ChannelConditionModel>()
            .AddConstructor<OSMBuildingCondition>();
        return id;
    }

    // `Load()` načíta dáta zo súboru alebo pamäte.
    void Load(const std::string& path) {
        std::ifstream file(path);
        if (!file) throw std::runtime_error("OSM ground building CSV missing: " + path);
        std::string line;
        std::getline(file, line);
        if (line != "id,height_m,polygon_xy_m")
            throw std::runtime_error("OSM ground building CSV header invalid");
        buildings_.clear(); grid_.clear(); std::set<std::string> ids;
        while (std::getline(file, line)) {
            if (line.empty()) continue;
            const auto first = line.find(','), second = line.find(',', first + 1);
            if (first == std::string::npos || second == std::string::npos ||
                line.find(',', second + 1) != std::string::npos)
                throw std::runtime_error("OSM ground building row invalid");
            Building b;
            b.id = line.substr(0, first);
            b.height = std::stod(line.substr(first + 1, second - first - 1));
            if (b.id.empty() || !ids.insert(b.id).second ||
                !std::isfinite(b.height) || b.height <= 0 || b.height > 500)
                throw std::runtime_error("OSM ground building identity/height invalid");
            std::stringstream points(line.substr(second + 1));
            std::string pair;
            while (std::getline(points, pair, ';')) {
                const auto colon = pair.find(':');
                if (colon == std::string::npos || pair.find(':', colon + 1) != std::string::npos)
                    throw std::runtime_error("OSM ground building point invalid");
                Point p{std::stod(pair.substr(0, colon)), std::stod(pair.substr(colon + 1))};
                if (!std::isfinite(p.x) || !std::isfinite(p.y) ||
                    p.x < -500 || p.x > 4500 || p.y < -500 || p.y > 4500)
                    throw std::runtime_error("OSM ground building point outside local frame");
                b.polygon.push_back(p);
            }
            if (b.polygon.size() < 3 || b.polygon.size() > 150)
                throw std::runtime_error("OSM ground building polygon invalid");
            b.xmin = b.xmax = b.polygon.front().x;
            b.ymin = b.ymax = b.polygon.front().y;
            for (const auto& p : b.polygon) {
                b.xmin = std::min(b.xmin, p.x); b.xmax = std::max(b.xmax, p.x);
                b.ymin = std::min(b.ymin, p.y); b.ymax = std::max(b.ymax, p.y);
            }
            if (b.xmax <= b.xmin || b.ymax <= b.ymin)
                throw std::runtime_error("OSM ground building polygon degenerate");
            const size_t index = buildings_.size();
            buildings_.push_back(std::move(b));
            const auto& saved = buildings_.back();
            for (int x = Cell(saved.xmin); x <= Cell(saved.xmax); ++x)
                for (int y = Cell(saved.ymin); y <= Cell(saved.ymax); ++y)
                    grid_[{x, y}].push_back(index);
            if (buildings_.size() > 50000)
                throw std::runtime_error("Ground building count exceeds 50000");
        }
        if (buildings_.empty()) throw std::runtime_error("OSM ground building CSV is empty");
    }

    size_t Count() const { return buildings_.size(); }

    double RoofAt(double x, double y) const {
        double roof = 0;
        const auto found = grid_.find({Cell(x), Cell(y)});
        if (found == grid_.end()) return roof;
        for (const size_t index : found->second) {
            const auto& building = buildings_[index];
            if (x >= building.xmin && x <= building.xmax &&
                y >= building.ymin && y <= building.ymax && Inside(building, x, y))
                roof = std::max(roof, building.height);
        }
        return roof;
    }

    ns3::Ptr<ns3::ChannelCondition> GetChannelCondition(
        ns3::Ptr<const ns3::MobilityModel> a,
        ns3::Ptr<const ns3::MobilityModel> b) const override {
        auto condition = ns3::CreateObject<ns3::ChannelCondition>();
        condition->SetO2iCondition(ns3::ChannelCondition::O2iConditionValue::O2O);
        condition->SetLosCondition(Blocked(a->GetPosition(), b->GetPosition())
            ? ns3::ChannelCondition::LosConditionValue::NLOS
            : ns3::ChannelCondition::LosConditionValue::LOS);
        return condition;
    }

    int64_t AssignStreams(int64_t) override { return 0; }

    bool Blocked(const ns3::Vector& a, const ns3::Vector& b) const {
        const double xmin = std::min(a.x, b.x), xmax = std::max(a.x, b.x);
        const double ymin = std::min(a.y, b.y), ymax = std::max(a.y, b.y);
        std::set<size_t> seen;
        for (int x = Cell(xmin); x <= Cell(xmax); ++x)
            for (int y = Cell(ymin); y <= Cell(ymax); ++y) {
                const auto found = grid_.find({x, y});
                if (found == grid_.end()) continue;
                for (const size_t index : found->second) {
                    if (!seen.insert(index).second) continue;
                    const auto& building = buildings_[index];
                    if (building.xmax < xmin || building.xmin > xmax ||
                        building.ymax < ymin || building.ymin > ymax) continue;
                    if (Crosses(building, a, b)) return true;
                }
            }
        return false;
    }

private:
    static int Cell(double x) { return static_cast<int>(std::floor(x / 100.0)); }
    static double Cross(Point a, Point b) { return a.x * b.y - a.y * b.x; }
    static bool Inside(const Building& building, double x, double y) {
        bool inside = false;
        const auto& poly = building.polygon;
        for (size_t i = 0, j = poly.size() - 1; i < poly.size(); j = i++) {
            const auto& p = poly[i]; const auto& q = poly[j];
            if ((p.y > y) != (q.y > y) &&
                x < (q.x - p.x) * (y - p.y) / (q.y - p.y) + p.x)
                inside = !inside;
        }
        return inside;
    }
    static bool Crosses(const Building& building, const ns3::Vector& a,
                        const ns3::Vector& b) {
        if ((a.z <= building.height && Inside(building, a.x, a.y)) ||
            (b.z <= building.height && Inside(building, b.x, b.y))) return true;
        Point origin{a.x, a.y}, ray{b.x - a.x, b.y - a.y};
        const auto& poly = building.polygon;
        for (size_t i = 0; i < poly.size(); ++i) {
            const Point p = poly[i], q = poly[(i + 1) % poly.size()];
            const Point edge{q.x - p.x, q.y - p.y};
            const double denominator = Cross(ray, edge);
            if (std::abs(denominator) < 1e-10) continue;
            const Point delta{p.x - origin.x, p.y - origin.y};
            const double t = Cross(delta, edge) / denominator;
            const double u = Cross(delta, ray) / denominator;
            if (t >= 0 && t <= 1 && u >= 0 && u <= 1 &&
                a.z + t * (b.z - a.z) <= building.height) return true;
        }
        return false;
    }

    std::vector<Building> buildings_;
    std::map<std::pair<int, int>, std::vector<size_t>> grid_;
};

} // namespace groundradio
#endif
