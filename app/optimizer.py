"""Dinamik rota optimizasyon motoru (saf Python, veritabanından bağımsız).

Akış:
1. Eşik filtresi: yalnızca doluluk >= eşik (varsayılan %80) veya kritik alarm veren konteynerler.
2. Mesafe matrisi: depo + seçilen konteynerler arasında haversine x şehir içi yol katsayısı.
3. Araçlara dağıtım: depo etrafında açısal tarama (sweep) + araç kapasite kısıtı.
4. Her araç için En Yakın Komşu (Nearest Neighbor) rotası, ardından 2-opt iyileştirmesi.
5. Tasarruf: statik çizelgeye (tüm konteynerler, sabit sıra) göre km, yakıt ve CO2 farkı.

İleride Google OR-Tools CVRP ile değiştirilebilmesi için arayüz `optimize()` fonksiyonunda toplandı.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

ROAD_FACTOR = 1.3  # kuş uçuşu mesafeden şehir içi yol mesafesine katsayı
AVG_SPEED_KMH = 25.0  # şehir içi ortalama hız
SERVICE_MIN_PER_STOP = 3.0  # konteyner başına boşaltma süresi
WASTE_DENSITY_KG_PER_L = 0.12  # konteyner içi evsel atık yoğunluğu
CO2_KG_PER_L_DIESEL = 2.68


@dataclass
class Stop:
    id: int
    lat: float
    lng: float
    fill_rate: float
    capacity_liters: int = 1100
    is_critical: bool = False

    @property
    def load_kg(self) -> float:
        return self.capacity_liters * (self.fill_rate / 100.0) * WASTE_DENSITY_KG_PER_L


@dataclass
class Truck:
    id: int
    capacity_kg: float
    fuel_l_per_100km: float = 35.0


@dataclass
class PlannedRoute:
    vehicle_id: int
    stop_ids: list[int]
    distance_km: float
    naive_distance_km: float  # aynı duraklar, optimizasyonsuz sırayla
    load_kg: float
    fuel_l: float
    duration_min: float
    etas_min: list[float] = field(default_factory=list)


@dataclass
class OptimizationOutput:
    routes: list[PlannedRoute]
    selected_ids: list[int]
    unassigned_ids: list[int]
    baseline_distance_km: float
    optimized_distance_km: float
    baseline_fuel_l: float
    optimized_fuel_l: float

    @property
    def distance_saved_km(self) -> float:
        return max(0.0, self.baseline_distance_km - self.optimized_distance_km)

    @property
    def fuel_saved_l(self) -> float:
        return max(0.0, self.baseline_fuel_l - self.optimized_fuel_l)

    @property
    def co2_reduced_kg(self) -> float:
        return self.fuel_saved_l * CO2_KG_PER_L_DIESEL


# ----------------------------------------------------------------- mesafe

def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def road_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    return haversine_km(a[0], a[1], b[0], b[1]) * ROAD_FACTOR


def distance_matrix(points: list[tuple[float, float]]) -> list[list[float]]:
    n = len(points)
    m = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            m[i][j] = m[j][i] = road_km(points[i], points[j])
    return m


def tour_length(tour: list[int], m: list[list[float]]) -> float:
    """tour: matris indeksleri, 0 = depo. Depodan çıkıp depoya döner."""
    if not tour:
        return 0.0
    path = [0, *tour, 0]
    return sum(m[path[i]][path[i + 1]] for i in range(len(path) - 1))


# ----------------------------------------------------------------- sezgiseller

def nearest_neighbor(indices: list[int], m: list[list[float]]) -> list[int]:
    remaining = set(indices)
    tour, cur = [], 0
    while remaining:
        nxt = min(remaining, key=lambda j: m[cur][j])
        tour.append(nxt)
        remaining.remove(nxt)
        cur = nxt
    return tour


def two_opt(tour: list[int], m: list[list[float]], max_passes: int = 50) -> list[int]:
    best = tour[:]
    if len(best) < 3:
        return best
    for _ in range(max_passes):
        improved = False
        path = [0, *best, 0]
        for i in range(1, len(path) - 2):
            for k in range(i + 1, len(path) - 1):
                a, b, c, d = path[i - 1], path[i], path[k], path[k + 1]
                delta = (m[a][c] + m[b][d]) - (m[a][b] + m[c][d])
                if delta < -1e-9:
                    path[i:k + 1] = reversed(path[i:k + 1])
                    improved = True
        best = path[1:-1]
        if not improved:
            break
    return best


def sweep_partition(
    depot: tuple[float, float],
    stops: list[Stop],
    trucks: list[Truck],
    balance: bool = True,
) -> tuple[list[list[Stop]], list[Stop]]:
    """Konteynerleri depo etrafındaki açıya göre sıralar, araç kapasitesine göre dilimler.

    balance=True ise yük araçlar arasında dengeli paylaştırılır (tek araç tüm şehri dolaşmaz).
    """
    order = sorted(stops, key=lambda s: math.atan2(s.lat - depot[0], s.lng - depot[1]))
    clusters: list[list[Stop]] = []
    i = 0
    for idx, truck in enumerate(trucks):
        remaining = order[i:]
        if not remaining:
            break
        left_trucks = len(trucks) - idx
        remaining_load = sum(s.load_kg for s in remaining)
        target = min(truck.capacity_kg, remaining_load / left_trucks * 1.1) if balance else truck.capacity_kg
        cluster, load = [], 0.0
        while i < len(order):
            l = order[i].load_kg
            if load + l > truck.capacity_kg:
                break
            if cluster and load + l > target:
                break
            cluster.append(order[i])
            load += l
            i += 1
        clusters.append(cluster)
    return clusters, order[i:]


# ----------------------------------------------------------------- ana fonksiyon

def select_candidates(stops: list[Stop], threshold: float) -> list[Stop]:
    return [s for s in stops if s.fill_rate >= threshold or s.is_critical]


def _baseline(depot, all_stops: list[Stop], n_vehicles: int, fuel_rate: float) -> float:
    """Statik çizelge: tüm konteynerler, sabit (kayıt) sırasıyla, araçlara eşit bölünmüş."""
    if not all_stops or n_vehicles <= 0:
        return 0.0
    ordered = sorted(all_stops, key=lambda s: s.id)
    size = math.ceil(len(ordered) / n_vehicles)
    total = 0.0
    for c in range(0, len(ordered), size):
        chunk = ordered[c:c + size]
        pts = [depot] + [(s.lat, s.lng) for s in chunk]
        total += tour_length(list(range(1, len(pts))), distance_matrix(pts))
    return total


def optimize(
    depot: tuple[float, float],
    all_stops: list[Stop],
    trucks: list[Truck],
    threshold: float = 80.0,
    balance: bool = True,
) -> OptimizationOutput:
    candidates = select_candidates(all_stops, threshold)
    # Kritik alarmlı ve en dolu konteynerler kapasite yetmezse önce alınsın
    candidates.sort(key=lambda s: (not s.is_critical, -s.fill_rate))
    fleet_cap = sum(t.capacity_kg for t in trucks)
    routable, overflow, acc = [], [], 0.0
    for s in candidates:
        if acc + s.load_kg <= fleet_cap * 0.95:
            routable.append(s)
            acc += s.load_kg
        else:
            overflow.append(s)

    clusters, leftover = sweep_partition(depot, routable, trucks, balance=balance)
    unassigned = overflow + leftover

    planned: list[PlannedRoute] = []
    for truck, cluster in zip(trucks, clusters):
        if not cluster:
            continue
        pts = [depot] + [(s.lat, s.lng) for s in cluster]
        m = distance_matrix(pts)
        idx = list(range(1, len(pts)))
        naive = tour_length(idx, m)
        # NN başlangıcı ile tarama (açısal) başlangıcını 2-opt ile iyileştir, kısa olanı seç
        tour = min((two_opt(nearest_neighbor(idx, m), m), two_opt(idx, m)),
                   key=lambda t: tour_length(t, m))
        dist = tour_length(tour, m)

        etas, t, prev = [], 0.0, 0
        for j in tour:
            t += m[prev][j] / AVG_SPEED_KMH * 60
            etas.append(round(t, 1))
            t += SERVICE_MIN_PER_STOP
            prev = j
        t += m[prev][0] / AVG_SPEED_KMH * 60

        planned.append(PlannedRoute(
            vehicle_id=truck.id,
            stop_ids=[cluster[j - 1].id for j in tour],
            distance_km=dist,
            naive_distance_km=naive,
            load_kg=sum(s.load_kg for s in cluster),
            fuel_l=dist * truck.fuel_l_per_100km / 100,
            duration_min=t,
            etas_min=etas,
        ))

    used = max(1, len(planned))
    avg_fuel = sum(t.fuel_l_per_100km for t in trucks) / len(trucks) if trucks else 35.0
    baseline_km = _baseline(depot, all_stops, used, avg_fuel)
    optimized_km = sum(r.distance_km for r in planned)
    return OptimizationOutput(
        routes=planned,
        selected_ids=[s.id for s in candidates],
        unassigned_ids=[s.id for s in unassigned],
        baseline_distance_km=baseline_km,
        optimized_distance_km=optimized_km,
        baseline_fuel_l=baseline_km * avg_fuel / 100,
        optimized_fuel_l=sum(r.fuel_l for r in planned),
    )
