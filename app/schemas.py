"""Pydantic istek/yanıt şemaları."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

VehicleStatus = Literal["idle", "on_route", "maintenance"]
RouteStatus = Literal["planned", "in_progress", "delayed", "completed", "replaced"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------- konteyner

class BinOut(ORMModel):
    id: int
    code: str
    zone_name: str
    latitude: float
    longitude: float
    capacity_liters: int
    fill_rate: float = Field(..., ge=0, le=100, description="Doluluk oranı (%)")
    is_critical: bool
    alarm_note: str | None = None
    last_updated: datetime
    needs_collection: bool = Field(False, description="Eşiği aşmış veya kritik alarm vermiş mi")


class BinUpdate(BaseModel):
    """IoT sensöründen gelen doluluk/alarm güncellemesi."""
    fill_rate: float | None = Field(None, ge=0, le=100, examples=[92.5])
    is_critical: bool | None = None
    alarm_note: str | None = Field(None, max_length=120)


# ---------------------------------------------------------------- araç

class VehicleOut(ORMModel):
    id: int
    code: str
    plate_number: str
    driver_name: str
    max_capacity_kg: float
    fuel_l_per_100km: float
    status: VehicleStatus
    current_lat: float
    current_lng: float


class VehicleStatusUpdate(BaseModel):
    status: VehicleStatus


# ---------------------------------------------------------------- rota

class OptimizeRequest(BaseModel):
    threshold: float = Field(80.0, ge=50, le=100, description="Rotaya alınacak minimum doluluk (%)")
    vehicle_ids: list[int] | None = Field(None, description="Boşsa bakımda olmayan tüm araçlar kullanılır")
    balance: bool = Field(True, description="Yükü araçlar arasında dengeli dağıt")
    persist: bool = Field(True, description="Rotaları veritabanına kaydet (False: yalnızca simülasyon)")


class StopOut(BaseModel):
    collection_id: int | None = None
    stop_order: int
    bin_id: int
    bin_code: str
    zone_name: str
    latitude: float
    longitude: float
    fill_rate: float
    is_critical: bool
    load_kg: float
    eta_minutes: float
    is_collected: bool = False


class RouteOut(BaseModel):
    route_id: int | None = None
    vehicle_id: int
    vehicle_code: str
    driver_name: str
    status: RouteStatus
    created_at: datetime | None = None
    stops: list[StopOut]
    path: list[tuple[float, float]] = Field(..., description="Depo → duraklar → depo koordinatları")
    total_distance_km: float
    naive_distance_km: float | None = Field(None, description="Aynı duraklar, optimizasyonsuz sıra")
    estimated_fuel_l: float
    load_kg: float
    capacity_kg: float
    duration_min: float
    progress_pct: float = 0.0
    next_stop: str | None = None


class OptimizationSummary(BaseModel):
    threshold: float
    total_bins: int
    selected_bins: int
    skipped_bins: int = Field(..., description="Eşik altında olduğu için ziyaret edilmeyen konteynerler")
    unassigned_bins: list[str]
    vehicles_used: int
    baseline_distance_km: float = Field(..., description="Statik çizelge: tüm konteynerler, sabit sıra")
    optimized_distance_km: float
    distance_saved_km: float
    distance_saved_pct: float
    baseline_fuel_l: float
    optimized_fuel_l: float
    fuel_saved_l: float
    co2_reduced_kg: float
    fuel_cost_saved_try: float


class OptimizeResponse(BaseModel):
    depot: dict
    summary: OptimizationSummary
    routes: list[RouteOut]


class ReassignRequest(BaseModel):
    vehicle_id: int = Field(..., description="Rotayı devralacak araç")


# ---------------------------------------------------------------- analitik

class KPIOut(BaseModel):
    total_bins: int
    critical_bins: int
    avg_fill_rate: float
    active_vehicles: int
    idle_vehicles: int
    maintenance_vehicles: int
    optimized_routes_today: int
    collections_completed_today: int
    collections_planned_today: int
    distance_saved_today_km: float
    fuel_saved_today_l: float
    co2_reduced_today_kg: float


class TrendPoint(BaseModel):
    date: str
    baseline_km: float
    optimized_km: float
    fuel_saved_l: float
    co2_reduced_kg: float


class ZoneFill(BaseModel):
    zone_name: str
    avg_fill_rate: float
    bins: int
    critical: int


class Insight(BaseModel):
    severity: Literal["info", "warning", "critical"]
    title: str
    detail: str
    action: str | None = Field(None, description="Ön yüzün çağırabileceği endpoint")
    action_label: str | None = None
    payload: dict | None = None


class SimulationTickOut(BaseModel):
    updated_bins: int
    new_critical: list[str]
    advanced_routes: list[int]
    delayed_routes: list[int]
