"""SQLAlchemy modelleri: bins, vehicles, routes, collections.

PostgreSQL ve MS SQL uyumluluğu için:
- Tüm String alanların uzunluğu açıkça verilir (MS SQL'de VARCHAR(MAX) yerine NVARCHAR(n)).
- Enum yerine kısa String + uygulama katmanında doğrulama kullanılır (iki motor da destekler).
- Tarihler timezone'suz UTC DateTime olarak saklanır (DATETIME2 / TIMESTAMP).
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Bin(Base):
    """Akıllı konteyner (IoT doluluk sensörlü)."""

    __tablename__ = "bins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    zone_name: Mapped[str] = mapped_column(String(80), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    capacity_liters: Mapped[int] = mapped_column(Integer, default=1100)
    fill_rate: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)  # yangın/koku/devrilme alarmı
    alarm_note: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    collections: Mapped[list["Collection"]] = relationship(back_populates="bin")


class Vehicle(Base):
    """Atık toplama aracı."""

    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # VH-101
    plate_number: Mapped[str] = mapped_column(String(20))
    driver_name: Mapped[str] = mapped_column(String(80))
    max_capacity_kg: Mapped[float] = mapped_column(Float, default=1500)
    fuel_l_per_100km: Mapped[float] = mapped_column(Float, default=35.0)
    status: Mapped[str] = mapped_column(String(20), default="idle")  # idle | on_route | maintenance
    current_lat: Mapped[float] = mapped_column(Float)
    current_lng: Mapped[float] = mapped_column(Float)

    routes: Mapped[list["Route"]] = relationship(back_populates="vehicle")


class Route(Base):
    """Optimizasyon motorunun bir araca atadığı toplama rotası."""

    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    # planned | in_progress | delayed | completed | replaced
    status: Mapped[str] = mapped_column(String(20), default="planned", index=True)
    threshold: Mapped[float] = mapped_column(Float, default=80.0)
    total_distance_km: Mapped[float] = mapped_column(Float, default=0.0)
    baseline_distance_km: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_fuel_l: Mapped[float] = mapped_column(Float, default=0.0)
    distance_saved_km: Mapped[float] = mapped_column(Float, default=0.0)
    fuel_saved_l: Mapped[float] = mapped_column(Float, default=0.0)
    co2_reduced_kg: Mapped[float] = mapped_column(Float, default=0.0)
    load_kg: Mapped[float] = mapped_column(Float, default=0.0)
    duration_min: Mapped[float] = mapped_column(Float, default=0.0)

    vehicle: Mapped[Vehicle] = relationship(back_populates="routes")
    collections: Mapped[list["Collection"]] = relationship(
        back_populates="route", order_by="Collection.stop_order", cascade="all, delete-orphan"
    )


class Collection(Base):
    """Rota üzerindeki bir durak / konteyner boşaltma kaydı."""

    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id"), index=True)
    bin_id: Mapped[int] = mapped_column(ForeignKey("bins.id"), index=True)
    stop_order: Mapped[int] = mapped_column(Integer)
    eta_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    fill_rate_at_plan: Mapped[float] = mapped_column(Float, default=0.0)
    load_kg: Mapped[float] = mapped_column(Float, default=0.0)
    is_collected: Mapped[bool] = mapped_column(Boolean, default=False)
    collected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    route: Mapped[Route] = relationship(back_populates="collections")
    bin: Mapped[Bin] = relationship(back_populates="collections")
