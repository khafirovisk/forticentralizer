from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import datetime


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Firewall(Base):
    __tablename__ = "firewalls"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    host = Column(String, nullable=False)
    port = Column(Integer, default=443)
    api_key = Column(String, nullable=False)
    serial = Column(String, default="")
    model = Column(String, default="")
    firmware = Column(String, default="")
    status = Column(String, default="unknown")
    last_seen = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    backups = relationship("Backup", back_populates="firewall", cascade="all, delete")
    security_ratings = relationship("SecurityRating", back_populates="firewall", cascade="all, delete")
    assets = relationship("Asset", back_populates="firewall", cascade="all, delete")


class Backup(Base):
    __tablename__ = "backups"
    id = Column(Integer, primary_key=True)
    firewall_id = Column(Integer, ForeignKey("firewalls.id"))
    filename = Column(String)
    file_path = Column(String)
    file_size = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    firewall = relationship("Firewall", back_populates="backups")


class SecurityRating(Base):
    __tablename__ = "security_ratings"
    id = Column(Integer, primary_key=True)
    firewall_id = Column(Integer, ForeignKey("firewalls.id"))
    posture_score = Column(Float, default=0)
    coverage_score = Column(Float, default=0)
    optimization_score = Column(Float, default=0)
    details_json = Column(Text, default="[]")
    collected_at = Column(DateTime, default=datetime.datetime.utcnow)

    firewall = relationship("Firewall", back_populates="security_ratings")


class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True)
    firewall_id = Column(Integer, ForeignKey("firewalls.id"))
    ip = Column(String, default="")
    mac = Column(String, default="")
    hostname = Column(String, default="")
    interface = Column(String, default="")
    device_type = Column(String, default="")
    collected_at = Column(DateTime, default=datetime.datetime.utcnow)

    firewall = relationship("Firewall", back_populates="assets")
