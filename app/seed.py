"""Örnek veri: Kadıköy (İstanbul) pilot bölgesi, 42 akıllı konteyner ve 5 araç.

Veriler deterministiktir (sabit random seed) — her sıfırlamada aynı başlangıç durumu oluşur.
"""
import random
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Bin, Collection, Route, Vehicle, utcnow

DEPOT = {"name": "Kadıköy Merkez Depo", "lat": 40.9935, "lng": 29.0405}

ZONES = [
    ("Moda", 40.9835, 29.0265),
    ("Yeldeğirmeni", 40.9965, 29.0300),
    ("Acıbadem", 41.0040, 29.0480),
    ("Koşuyolu", 41.0120, 29.0390),
    ("Göztepe", 40.9790, 29.0640),
    ("Fenerbahçe", 40.9725, 29.0400),
    ("Caddebostan", 40.9665, 29.0625),
]

VEHICLES = [
    ("VH-101", "34 ECO 101", "Murat Yılmaz", 1400, 34.0, "idle"),
    ("VH-102", "34 ECO 102", "Ayşe Demir", 1400, 35.0, "idle"),
    ("VH-103", "34 ECO 103", "Emre Kaya", 1200, 33.0, "idle"),
    ("VH-104", "34 ECO 104", "Selin Aksoy", 1600, 37.0, "idle"),
    ("VH-105", "34 ECO 105", "Kerem Şahin", 1400, 35.0, "maintenance"),
]


def seed(db: Session, force: bool = False) -> bool:
    """Tablolar boşsa (veya force=True ise) örnek veriyi yükler. Yükleme yapıldıysa True döner."""
    if not force and db.scalar(select(func.count(Bin.id))):
        return False

    if force:
        db.query(Collection).delete()
        db.query(Route).delete()
        db.query(Vehicle).delete()
        db.query(Bin).delete()
        db.commit()

    rng = random.Random(42)
    now = utcnow()
    n = 0
    for zone, lat, lng in ZONES:
        for _ in range(6):
            n += 1
            # Yaklaşık üçte biri eşiğin üzerinde olacak şekilde doluluk dağılımı
            roll = rng.random()
            fill = rng.uniform(80, 99) if roll < 0.36 else rng.uniform(12, 78)
            db.add(Bin(
                code=f"KD-{n:03d}",
                zone_name=zone,
                latitude=round(lat + rng.uniform(-0.0035, 0.0035), 6),
                longitude=round(lng + rng.uniform(-0.0045, 0.0045), 6),
                capacity_liters=rng.choice([770, 1100, 1100]),
                fill_rate=round(fill, 1),
                last_updated=now - timedelta(minutes=rng.randint(1, 25)),
            ))
    db.flush()

    # İki konteynerde eşik altı olmasına rağmen kritik alarm
    for code, note in (("KD-009", "Koku sensörü alarmı"), ("KD-031", "Konteyner devrilme alarmı")):
        b = db.scalar(select(Bin).where(Bin.code == code))
        if b:
            b.is_critical, b.alarm_note = True, note

    vehicles = []
    for code, plate, driver, cap, fuel, status in VEHICLES:
        v = Vehicle(code=code, plate_number=plate, driver_name=driver, max_capacity_kg=cap,
                    fuel_l_per_100km=fuel, status=status, current_lat=DEPOT["lat"], current_lng=DEPOT["lng"])
        db.add(v)
        vehicles.append(v)
    db.flush()

    # Geçmiş 6 güne ait tamamlanmış rota özetleri (haftalık trend grafiği için örnek geçmiş)
    for day in range(6, 0, -1):
        for v in vehicles[:4]:
            base = rng.uniform(16, 24)
            opt = base * rng.uniform(0.55, 0.75)
            fuel = opt * v.fuel_l_per_100km / 100
            saved_fuel = (base - opt) * v.fuel_l_per_100km / 100
            db.add(Route(
                vehicle_id=v.id, created_at=now - timedelta(days=day, hours=rng.randint(0, 3)),
                status="completed", threshold=80, total_distance_km=round(opt, 2),
                baseline_distance_km=round(base, 2), estimated_fuel_l=round(fuel, 2),
                distance_saved_km=round(base - opt, 2), fuel_saved_l=round(saved_fuel, 2),
                co2_reduced_kg=round(saved_fuel * 2.68, 2), load_kg=round(rng.uniform(500, 1100), 1),
                duration_min=round(rng.uniform(45, 80), 1),
            ))
    db.commit()
    return True
