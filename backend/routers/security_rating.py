import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import datetime
from database import get_db
from models import Firewall, SecurityRating
from auth import get_current_user
from services.fortigate import get_security_rating

router = APIRouter(prefix="/security-rating", tags=["security-rating"])


@router.get("")
def list_security_ratings(db: Session = Depends(get_db), _=Depends(get_current_user)):
    firewalls = db.query(Firewall).all()
    result = []
    for fw in firewalls:
        latest = (
            db.query(SecurityRating)
            .filter(SecurityRating.firewall_id == fw.id)
            .order_by(SecurityRating.collected_at.desc())
            .first()
        )
        result.append({
            "firewall_id": fw.id,
            "firewall_name": fw.name,
            "serial": fw.serial,
            "model": fw.model,
            "status": fw.status,
            "posture_score": latest.posture_score if latest else None,
            "coverage_score": latest.coverage_score if latest else None,
            "optimization_score": latest.optimization_score if latest else None,
            "collected_at": latest.collected_at.isoformat() if latest else None,
        })
    return result


@router.get("/{fw_id}/details")
def get_rating_details(fw_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    fw = db.query(Firewall).filter(Firewall.id == fw_id).first()
    if not fw:
        raise HTTPException(status_code=404, detail="Firewall não encontrado")
    latest = (
        db.query(SecurityRating)
        .filter(SecurityRating.firewall_id == fw_id)
        .order_by(SecurityRating.collected_at.desc())
        .first()
    )
    if not latest:
        raise HTTPException(status_code=404, detail="Nenhum dado de Security Rating coletado ainda")
    return {
        "firewall_name": fw.name,
        "serial": fw.serial,
        "posture_score": latest.posture_score,
        "coverage_score": latest.coverage_score,
        "optimization_score": latest.optimization_score,
        "collected_at": latest.collected_at.isoformat(),
        "controls": json.loads(latest.details_json),
    }


@router.post("/{fw_id}/refresh")
def refresh_security_rating(fw_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    fw = db.query(Firewall).filter(Firewall.id == fw_id).first()
    if not fw:
        raise HTTPException(status_code=404, detail="Firewall não encontrado")

    success, data = get_security_rating(fw.host, fw.port, fw.api_key)
    if not success:
        raise HTTPException(status_code=502, detail=f"Falha ao coletar Security Rating: {data.get('error')}")

    rating = SecurityRating(
        firewall_id=fw.id,
        posture_score=data["posture"],
        coverage_score=data["coverage"],
        optimization_score=data["optimization"],
        details_json=json.dumps(data["controls"]),
    )
    db.add(rating)
    db.commit()
    return {
        "firewall_name": fw.name,
        "posture_score": data["posture"],
        "coverage_score": data["coverage"],
        "optimization_score": data["optimization"],
        "controls_count": len(data["controls"]),
    }
