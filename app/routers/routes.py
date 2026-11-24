"""EcoRoute API uç noktaları: konteynerler, araçlar, rota optimizasyonu, analitik ve simülasyon."""
import os
import random
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..database import get_db
from ..optimizer import CO2_KG_PER_L_DIESEL, WASTE_DENSITY_KG_PER_L, Stop, Truck, optimize
from ..seed import DEPOT, seed

router = APIRouter(prefix="/api")

DEFAULT_THRESHOLD = 80.0
ACTIVE_ROUTE_STATUSES = ("planned", "in_progress", "delayed")
FUEL_PRICE_TRY = float(os.getenv("FUEL_PRICE_TRY", "45"))  # motorin litre fiyatı, ortamdan ayarlanabilir
_rng = random.Random()


# ======================================================================= yardımcılar

def _today_start() -> datetime:
    now = models.utcnow()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _bin_out(b: models.Bin, threshold: float = DEFAULT_THRESHOLD) -> schemas.BinOut:
    out = schemas.BinOut.model_validate(b)
    out.needs_collection = b.fill_rate >= threshold or b.is_critical
    return out


def _get_or_404(db: Session, model, obj_id: int, label: str):
    obj = db.get(model, obj_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"{label} bulunamadı (id={obj_id})")
    return obj


def _active_routes(db: Session) -> list[models.Route]:
    return list(db.scalars(
        select(models.Route)
        .where(models.Route.status.in_(ACTIVE_ROUTE_STATUSES))
        .options(selectinload(models.Route.collections).selectinload(models.Collection.bin),
                 selectinload(models.Route.vehicle))
        .order_by(models.Route.id)
    ))


def _route_out(r: models.Route) -> schemas.RouteOut:
    stops = [
        schemas.StopOut(
            collection_id=c.id, stop_order=c.stop_order, bin_id=c.bin_id, bin_code=c.bin.code,
            zone_name=c.bin.zone_name, latitude=c.bin.latitude, longitude=c.bin.longitude,
            fill_rate=c.fill_rate_at_plan, is_critical=c.bin.is_critical, load_kg=round(c.load_kg, 1),
            eta_minutes=c.eta_minutes, is_collected=c.is_collected,
        )
        for c in r.collections
    ]
    done = sum(1 for s in stops if s.is_collected)
    nxt = next((s.bin_code for s in stops if not s.is_collected), None)
    depot = (DEPOT["lat"], DEPOT["lng"])
    return schemas.RouteOut(
        route_id=r.id, vehicle_id=r.vehicle_id, vehicle_code=r.vehicle.code,
        driver_name=r.vehicle.driver_name, status=r.status, created_at=r.created_at, stops=stops,
        path=[depot, *[(s.latitude, s.longitude) for s in stops], depot] if stops else [],
        total_distance_km=round(r.total_distance_km, 2), estimated_fuel_l=round(r.estimated_fuel_l, 2),
        load_kg=round(r.load_kg, 1), capacity_kg=r.vehicle.max_capacity_kg,
        duration_min=round(r.duration_min, 1),
        progress_pct=round(100 * done / len(stops), 1) if stops else (100.0 if r.status == "completed" else 0.0),
        next_stop=nxt if r.status != "completed" else None,
    )


def _collect_next(db: Session, r: models.Route) -> models.Collection | None:
    """Rotadaki sıradaki durağı boşaltılmış olarak işaretler; rota biterse aracı depoya döndürür."""
    nxt = next((c for c in r.collections if not c.is_collected), None)
    v = r.vehicle
    if nxt is None:
        r.status, v.status = "completed", "idle"
        v.current_lat, v.current_lng = DEPOT["lat"], DEPOT["lng"]
        return None
    nxt.is_collected, nxt.collected_at = True, models.utcnow()
    nxt.bin.fill_rate = round(_rng.uniform(0, 5), 1)
    nxt.bin.is_critical, nxt.bin.alarm_note = False, None
    nxt.bin.last_updated = models.utcnow()
    v.current_lat, v.current_lng, v.status = nxt.bin.latitude, nxt.bin.longitude, "on_route"
    if r.status == "planned":
        r.status = "in_progress"
    if all(c.is_collected for c in r.collections):
        r.status, v.status = "completed", "idle"
        v.current_lat, v.current_lng = DEPOT["lat"], DEPOT["lng"]
    return nxt


# ======================================================================= konteynerler

@router.get("/depot", tags=["Konteynerler"], summary="Ana depo konumu")
def get_depot():
    return DEPOT


@router.get("/bins", response_model=list[schemas.BinOut], tags=["Konteynerler"],
            summary="Konteynerleri listele",
            description="Tüm akıllı konteynerleri doluluk ve alarm bilgisiyle döndürür. Bölge, minimum doluluk ve kritik filtresi uygulanabilir.")
def list_bins(
    zone: str | None = Query(None, description="Bölge adı, örn. Moda"),
    min_fill: float = Query(0, ge=0, le=100),
    only_critical: bool = False,
    db: Session = Depends(get_db),
):
    q = select(models.Bin).where(models.Bin.fill_rate >= min_fill)
    if zone:
        q = q.where(models.Bin.zone_name == zone)
    if only_critical:
        q = q.where(models.Bin.is_critical == True)  # noqa: E712  (MS SQL: "= 1")
    return [_bin_out(b) for b in db.scalars(q.order_by(models.Bin.id))]


@router.get("/bins/critical", response_model=list[schemas.BinOut], tags=["Konteynerler"],
            summary="Toplanması gereken konteynerler",
            description="Doluluğu eşik değerin (varsayılan %80) üzerinde olan veya kritik alarm veren konteynerler, en doludan başlayarak.")
def critical_bins(threshold: float = Query(DEFAULT_THRESHOLD, ge=50, le=100), db: Session = Depends(get_db)):
    q = select(models.Bin).where((models.Bin.fill_rate >= threshold) | (models.Bin.is_critical == True))  # noqa: E712  (MS SQL: "= 1")
    return [_bin_out(b, threshold) for b in db.scalars(q.order_by(models.Bin.fill_rate.desc()))]


@router.get("/bins/{bin_id}", response_model=schemas.BinOut, tags=["Konteynerler"], summary="Tek konteyner")
def get_bin(bin_id: int, db: Session = Depends(get_db)):
    return _bin_out(_get_or_404(db, models.Bin, bin_id, "Konteyner"))


@router.patch("/bins/{bin_id}", response_model=schemas.BinOut, tags=["Konteynerler"],
              summary="Sensör verisi güncelle",
              description="IoT sensöründen gelen doluluk oranı veya alarm bilgisini kaydeder.")
def update_bin(bin_id: int, payload: schemas.BinUpdate, db: Session = Depends(get_db)):
    b = _get_or_404(db, models.Bin, bin_id, "Konteyner")
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Güncellenecek alan gönderilmedi")
    for k, v in data.items():
        setattr(b, k, v)
    if data.get("is_critical") is False:
        b.alarm_note = None
    b.last_updated = models.utcnow()
    db.commit()
    return _bin_out(b)


# ======================================================================= araçlar

@router.get("/vehicles", response_model=list[schemas.VehicleOut], tags=["Araçlar"], summary="Araç filosu")
def list_vehicles(db: Session = Depends(get_db)):
    return list(db.scalars(select(models.Vehicle).order_by(models.Vehicle.id)))


@router.patch("/vehicles/{vehicle_id}/status", response_model=schemas.VehicleOut, tags=["Araçlar"],
              summary="Araç durumunu değiştir",
              description="Aktif rotası olan araç bakıma alınamaz; önce rotayı başka araca devredin.")
def update_vehicle_status(vehicle_id: int, payload: schemas.VehicleStatusUpdate, db: Session = Depends(get_db)):
    v = _get_or_404(db, models.Vehicle, vehicle_id, "Araç")
    if payload.status == "maintenance" and any(r.vehicle_id == v.id for r in _active_routes(db)):
        raise HTTPException(status.HTTP_409_CONFLICT,
                            detail=f"{v.code} aktif bir rotada. Önce rotayı başka araca devredin.")
    v.status = payload.status
    db.commit()
    return v


# ======================================================================= rota optimizasyonu

@router.post("/routes/optimize", response_model=schemas.OptimizeResponse, tags=["Rota Optimizasyonu"],
             summary="Dinamik rota hesapla",
             description=(
                 "Doluluğu eşik değerin üzerinde (varsayılan %80) veya kritik alarm veren konteynerleri seçer, "
                 "araç kapasitesine göre bölgelere ayırır, her araç için En Yakın Komşu + 2-opt rotası üretir ve "
                 "statik çizelgeye göre km / yakıt / CO₂ tasarrufunu hesaplar. Aktif rotadaki araç ve konteynerler "
                 "yeni plana dahil edilmez; bekleyen (planned) rotalar yenisiyle değiştirilir."
             ))
def optimize_routes(payload: schemas.OptimizeRequest, db: Session = Depends(get_db)):
    active = _active_routes(db)
    if payload.persist:
        for r in active:
            if r.status == "planned" and not any(c.is_collected for c in r.collections):
                r.status = "replaced"
                r.vehicle.status = "idle"
        db.flush()
        active = [r for r in active if r.status != "replaced"]

    busy_vehicles = {r.vehicle_id for r in active}
    busy_bins = {c.bin_id for r in active for c in r.collections if not c.is_collected}

    vq = select(models.Vehicle).where(models.Vehicle.status != "maintenance")
    if payload.vehicle_ids:
        vq = vq.where(models.Vehicle.id.in_(payload.vehicle_ids))
    vehicles = [v for v in db.scalars(vq.order_by(models.Vehicle.id)) if v.id not in busy_vehicles]
    if not vehicles:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT,
                            detail="Uygun araç yok: tüm araçlar bakımda veya aktif rotada.")

    all_bins = list(db.scalars(select(models.Bin).order_by(models.Bin.id)))
    if not all_bins:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Kayıtlı konteyner yok. /api/seed/reset ile örnek veri yükleyin.")
    bins_by_id = {b.id: b for b in all_bins}
    stops = [Stop(b.id, b.latitude, b.longitude, b.fill_rate, b.capacity_liters, b.is_critical)
             for b in all_bins if b.id not in busy_bins]
    if not any(s.fill_rate >= payload.threshold or s.is_critical for s in stops):
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            detail=f"Doluluğu %{payload.threshold:g} eşiğini aşan veya alarm veren konteyner yok.")

    trucks = [Truck(v.id, v.max_capacity_kg, v.fuel_l_per_100km) for v in vehicles]
    depot = (DEPOT["lat"], DEPOT["lng"])
    result = optimize(depot, stops, trucks, threshold=payload.threshold, balance=payload.balance)
    vmap = {v.id: v for v in vehicles}

    total_saved_fuel = result.fuel_saved_l
    routes_out: list[schemas.RouteOut] = []
    for pr in result.routes:
        v = vmap[pr.vehicle_id]
        # Toplam tasarrufu rotalara mesafe payına göre dağıt (raporlama için)
        share = pr.distance_km / result.optimized_distance_km if result.optimized_distance_km else 0
        stop_bins = [bins_by_id[i] for i in pr.stop_ids]
        stop_out = [
            schemas.StopOut(
                stop_order=n + 1, bin_id=b.id, bin_code=b.code, zone_name=b.zone_name,
                latitude=b.latitude, longitude=b.longitude, fill_rate=b.fill_rate, is_critical=b.is_critical,
                load_kg=round(b.capacity_liters * b.fill_rate / 100 * WASTE_DENSITY_KG_PER_L, 1),
                eta_minutes=pr.etas_min[n],
            )
            for n, b in enumerate(stop_bins)
        ]
        route_id = None
        if payload.persist:
            r = models.Route(
                vehicle_id=v.id, status="planned", threshold=payload.threshold,
                total_distance_km=round(pr.distance_km, 3),
                baseline_distance_km=round(result.baseline_distance_km * share, 3),
                estimated_fuel_l=round(pr.fuel_l, 3),
                distance_saved_km=round(result.distance_saved_km * share, 3),
                fuel_saved_l=round(total_saved_fuel * share, 3),
                co2_reduced_kg=round(total_saved_fuel * share * CO2_KG_PER_L_DIESEL, 3),
                load_kg=round(pr.load_kg, 1), duration_min=round(pr.duration_min, 1),
            )
            r.collections = [
                models.Collection(bin_id=s.bin_id, stop_order=s.stop_order, eta_minutes=s.eta_minutes,
                                  fill_rate_at_plan=s.fill_rate, load_kg=s.load_kg)
                for s in stop_out
            ]
            db.add(r)
            db.flush()
            route_id = r.id
            v.status = "on_route"
            for s, c in zip(stop_out, r.collections):
                s.collection_id = c.id
        routes_out.append(schemas.RouteOut(
            route_id=route_id, vehicle_id=v.id, vehicle_code=v.code, driver_name=v.driver_name,
            status="planned", created_at=models.utcnow(), stops=stop_out,
            path=[depot, *[(s.latitude, s.longitude) for s in stop_out], depot],
            total_distance_km=round(pr.distance_km, 2), naive_distance_km=round(pr.naive_distance_km, 2),
            estimated_fuel_l=round(pr.fuel_l, 2), load_kg=round(pr.load_kg, 1),
            capacity_kg=v.max_capacity_kg, duration_min=round(pr.duration_min, 1),
            next_stop=stop_out[0].bin_code if stop_out else None,
        ))

    if payload.persist:
        db.commit()
    else:
        db.rollback()

    base = result.baseline_distance_km
    summary = schemas.OptimizationSummary(
        threshold=payload.threshold, total_bins=len(all_bins), selected_bins=len(result.selected_ids),
        skipped_bins=len(stops) - len(result.selected_ids),
        unassigned_bins=[bins_by_id[i].code for i in result.unassigned_ids],
        vehicles_used=len(result.routes),
        baseline_distance_km=round(base, 2), optimized_distance_km=round(result.optimized_distance_km, 2),
        distance_saved_km=round(result.distance_saved_km, 2),
        distance_saved_pct=round(100 * result.distance_saved_km / base, 1) if base else 0.0,
        baseline_fuel_l=round(result.baseline_fuel_l, 2), optimized_fuel_l=round(result.optimized_fuel_l, 2),
        fuel_saved_l=round(result.fuel_saved_l, 2), co2_reduced_kg=round(result.co2_reduced_kg, 2),
        fuel_cost_saved_try=round(result.fuel_saved_l * FUEL_PRICE_TRY, 2),
    )
    return schemas.OptimizeResponse(depot=DEPOT, summary=summary, routes=routes_out)


@router.get("/routes", response_model=list[schemas.RouteOut], tags=["Rota Optimizasyonu"],
            summary="Rotaları listele",
            description="Varsayılan olarak yalnızca aktif (planned / in_progress / delayed) rotalar döner.")
def list_routes(active_only: bool = True, limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    if active_only:
        return [_route_out(r) for r in _active_routes(db)]
    q = (select(models.Route)
         .options(selectinload(models.Route.collections).selectinload(models.Collection.bin),
                  selectinload(models.Route.vehicle))
         .order_by(models.Route.created_at.desc()).limit(limit))
    return [_route_out(r) for r in db.scalars(q)]


@router.get("/routes/{route_id}", response_model=schemas.RouteOut, tags=["Rota Optimizasyonu"], summary="Rota detayı")
def get_route(route_id: int, db: Session = Depends(get_db)):
    return _route_out(_get_or_404(db, models.Route, route_id, "Rota"))


@router.post("/routes/{route_id}/advance", response_model=schemas.RouteOut, tags=["Rota Optimizasyonu"],
             summary="Sıradaki durağı boşaltıldı işaretle",
             description="Sürücü uygulamasından gelen 'konteyner boşaltıldı' bildirimini simüle eder.")
def advance_route(route_id: int, db: Session = Depends(get_db)):
    r = _get_or_404(db, models.Route, route_id, "Rota")
    if r.status not in ACTIVE_ROUTE_STATUSES:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"Rota aktif değil (durum: {r.status})")
    _collect_next(db, r)
    db.commit()
    return _route_out(r)


@router.post("/routes/{route_id}/reassign", response_model=schemas.RouteOut, tags=["Rota Optimizasyonu"],
             summary="Rotayı başka araca devret",
             description="Geciken veya arızalanan aracın kalan duraklarını boştaki başka bir araca aktarır.")
def reassign_route(route_id: int, payload: schemas.ReassignRequest, db: Session = Depends(get_db)):
    r = _get_or_404(db, models.Route, route_id, "Rota")
    target = _get_or_404(db, models.Vehicle, payload.vehicle_id, "Araç")
    if r.status not in ACTIVE_ROUTE_STATUSES:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"Rota aktif değil (durum: {r.status})")
    if target.id == r.vehicle_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Rota zaten bu araçta")
    if target.status == "maintenance":
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"{target.code} bakımda")
    if any(a.vehicle_id == target.id for a in _active_routes(db)):
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"{target.code} zaten aktif bir rotada")
    remaining_kg = sum(c.load_kg for c in r.collections if not c.is_collected)
    if remaining_kg > target.max_capacity_kg:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            detail=f"{target.code} kapasitesi yetersiz ({remaining_kg:.0f} kg > {target.max_capacity_kg:.0f} kg)")
    old = r.vehicle
    old.status = "idle"
    r.vehicle_id, r.vehicle = target.id, target
    target.status = "on_route"
    r.status = "in_progress"
    db.commit()
    return _route_out(r)


# ======================================================================= analitik

@router.get("/analytics/kpis", response_model=schemas.KPIOut, tags=["Analitik"], summary="Üst KPI kartları")
def kpis(threshold: float = Query(DEFAULT_THRESHOLD, ge=50, le=100), db: Session = Depends(get_db)):
    bins = list(db.scalars(select(models.Bin)))
    vehicles = list(db.scalars(select(models.Vehicle)))
    today = list(db.scalars(
        select(models.Route).where(models.Route.created_at >= _today_start(), models.Route.status != "replaced")
        .options(selectinload(models.Route.collections))
    ))
    cols = [c for r in today for c in r.collections]
    return schemas.KPIOut(
        total_bins=len(bins),
        critical_bins=sum(1 for b in bins if b.fill_rate >= threshold or b.is_critical),
        avg_fill_rate=round(sum(b.fill_rate for b in bins) / len(bins), 1) if bins else 0.0,
        active_vehicles=sum(1 for v in vehicles if v.status == "on_route"),
        idle_vehicles=sum(1 for v in vehicles if v.status == "idle"),
        maintenance_vehicles=sum(1 for v in vehicles if v.status == "maintenance"),
        optimized_routes_today=len(today),
        collections_completed_today=sum(1 for c in cols if c.is_collected),
        collections_planned_today=len(cols),
        distance_saved_today_km=round(sum(r.distance_saved_km for r in today), 2),
        fuel_saved_today_l=round(sum(r.fuel_saved_l for r in today), 2),
        co2_reduced_today_kg=round(sum(r.co2_reduced_kg for r in today), 2),
    )


@router.get("/analytics/trend", response_model=list[schemas.TrendPoint], tags=["Analitik"],
            summary="Günlük verimlilik trendi", description="Son N günün statik çizelge ve optimize rota mesafeleri.")
def trend(days: int = Query(7, ge=1, le=90), db: Session = Depends(get_db)):
    start = _today_start() - timedelta(days=days - 1)
    rows = db.scalars(select(models.Route).where(models.Route.created_at >= start, models.Route.status != "replaced"))
    agg: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
    for r in rows:
        a = agg[r.created_at.strftime("%Y-%m-%d")]
        a[0] += r.baseline_distance_km
        a[1] += r.total_distance_km
        a[2] += r.fuel_saved_l
        a[3] += r.co2_reduced_kg
    out = []
    for i in range(days):
        d = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        a = agg.get(d, [0.0] * 4)
        out.append(schemas.TrendPoint(date=d, baseline_km=round(a[0], 2), optimized_km=round(a[1], 2),
                                      fuel_saved_l=round(a[2], 2), co2_reduced_kg=round(a[3], 2)))
    return out


@router.get("/analytics/zones", response_model=list[schemas.ZoneFill], tags=["Analitik"], summary="Bölge bazlı doluluk")
def zones(threshold: float = Query(DEFAULT_THRESHOLD, ge=50, le=100), db: Session = Depends(get_db)):
    groups: dict[str, list[models.Bin]] = defaultdict(list)
    for b in db.scalars(select(models.Bin)):
        groups[b.zone_name].append(b)
    out = [
        schemas.ZoneFill(zone_name=z, bins=len(bs), avg_fill_rate=round(sum(b.fill_rate for b in bs) / len(bs), 1),
                         critical=sum(1 for b in bs if b.fill_rate >= threshold or b.is_critical))
        for z, bs in groups.items()
    ]
    return sorted(out, key=lambda z: -z.avg_fill_rate)


@router.get("/analytics/insights", response_model=list[schemas.Insight], tags=["Analitik"],
            summary="Yapay zeka karar destek önerileri (Next Best Action)",
            description="Saha durumuna göre kural tabanlı, tek tıkla uygulanabilir aksiyon önerileri üretir.")
def insights(threshold: float = Query(DEFAULT_THRESHOLD, ge=50, le=100), db: Session = Depends(get_db)):
    out: list[schemas.Insight] = []
    active = _active_routes(db)
    on_route_bins = {c.bin_id for r in active for c in r.collections if not c.is_collected}
    bins = list(db.scalars(select(models.Bin)))
    vehicles = list(db.scalars(select(models.Vehicle)))
    busy = {r.vehicle_id for r in active}
    idle = [v for v in vehicles if v.status != "maintenance" and v.id not in busy]

    for r in active:
        if r.status != "delayed":
            continue
        remaining = sum(c.load_kg for c in r.collections if not c.is_collected)
        cand = next((v for v in sorted(idle, key=lambda v: -v.max_capacity_kg) if v.max_capacity_kg >= remaining), None)
        left = sum(1 for c in r.collections if not c.is_collected)
        if cand:
            out.append(schemas.Insight(
                severity="critical", title=f"{r.vehicle.code} gecikmede",
                detail=f"Kalan {left} durağı boştaki {cand.code} aracına devretmek tahmini gecikmeyi azaltır.",
                action=f"/api/routes/{r.id}/reassign", action_label=f"{cand.code} aracına devret",
                payload={"vehicle_id": cand.id}))
        else:
            out.append(schemas.Insight(severity="critical", title=f"{r.vehicle.code} gecikmede",
                                       detail=f"Kalan {left} durak için uygun boş araç yok."))

    pending = [b for b in bins if (b.fill_rate >= threshold or b.is_critical) and b.id not in on_route_bins]
    if pending:
        alarms = [b for b in pending if b.is_critical]
        detail = f"{len(pending)} konteyner eşiği aştı veya alarm verdi ancak henüz rotada değil"
        if alarms:
            detail += f" (alarm: {', '.join(b.code for b in alarms[:3])})"
        out.append(schemas.Insight(
            severity="warning" if idle else "critical", title="Rotasız acil konteynerler",
            detail=detail + (f". {len(idle)} araç müsait." if idle else ". Müsait araç yok."),
            action="/api/routes/optimize" if idle else None,
            action_label="Rotaları yeniden hesapla" if idle else None,
            payload={"threshold": threshold} if idle else None))

    near = [b for b in bins if threshold - 10 <= b.fill_rate < threshold and b.id not in on_route_bins]
    if near:
        zone_counts: dict[str, int] = defaultdict(int)
        for b in near:
            zone_counts[b.zone_name] += 1
        z, c = max(zone_counts.items(), key=lambda x: x[1])
        out.append(schemas.Insight(severity="info", title="Yakında eşiğe ulaşacaklar",
                                   detail=f"{len(near)} konteyner %{threshold - 10:g}–%{threshold:g} aralığında; en çok {z} bölgesinde ({c})."))

    maint = [v.code for v in vehicles if v.status == "maintenance"]
    if maint:
        out.append(schemas.Insight(severity="info", title="Bakımdaki araçlar",
                                   detail=f"{', '.join(maint)} bakımda; filo kapasitesi buna göre planlandı."))
    if not out:
        out.append(schemas.Insight(severity="info", title="Her şey yolunda",
                                   detail="Eşiği aşan rotasız konteyner veya geciken araç yok."))
    return out


# ======================================================================= simülasyon

@router.post("/simulate/tick", response_model=schemas.SimulationTickOut, tags=["IoT Simülasyonu"],
             summary="Sensör ve saha simülasyonu adımı",
             description="Konteyner doluluklarını bölge yoğunluğuna göre artırır, aktif rotalarda bir durak ilerletir ve "
                         "rastgele trafik gecikmesi / sensör alarmı üretir.")
def simulate_tick(advance_routes: bool = True, db: Session = Depends(get_db)):
    active = _active_routes(db)
    on_route = {c.bin_id for r in active for c in r.collections if not c.is_collected}
    zone_rate = {"Moda": 1.4, "Yeldeğirmeni": 1.3, "Caddebostan": 1.2}
    new_crit, updated = [], 0
    for b in db.scalars(select(models.Bin)):
        if b.id in on_route:
            continue
        b.fill_rate = round(min(100.0, b.fill_rate + _rng.uniform(0.3, 2.5) * zone_rate.get(b.zone_name, 1.0)), 1)
        b.last_updated = models.utcnow()
        updated += 1
        if not b.is_critical and _rng.random() < 0.004:
            b.is_critical, b.alarm_note = True, _rng.choice(["Koku sensörü alarmı", "Sıcaklık alarmı"])
            new_crit.append(b.code)

    advanced, delayed = [], []
    if advance_routes:
        for r in active:
            if r.status == "in_progress" and _rng.random() < 0.08:
                r.status = "delayed"
                delayed.append(r.id)
                continue
            if r.status == "delayed":  # gecikmedeki araç yavaş ilerler
                if _rng.random() < 0.35:
                    _collect_next(db, r)
                    advanced.append(r.id)
                continue
            _collect_next(db, r)
            advanced.append(r.id)
    db.commit()
    return schemas.SimulationTickOut(updated_bins=updated, new_critical=new_crit,
                                     advanced_routes=advanced, delayed_routes=delayed)


@router.post("/seed/reset", tags=["IoT Simülasyonu"], summary="Örnek veriyi sıfırla",
             description="Tüm tabloları temizler ve Kadıköy pilot bölgesi örnek verisini yeniden yükler.")
def reset_seed(db: Session = Depends(get_db)):
    seed(db, force=True)
    return {"ok": True, "message": "Örnek veri yeniden yüklendi"}
