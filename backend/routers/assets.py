from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import datetime
from database import get_db
from models import Firewall, Asset
from auth import get_current_user
from services.fortigate import get_assets

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("")
def list_all_assets(db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Global inverted view: all assets from all firewalls"""
    assets = db.query(Asset).all()
    return [
        {
            "id": a.id,
            "ip": a.ip,
            "mac": a.mac,
            "hostname": a.hostname,
            "interface": a.interface,
            "device_type": a.device_type,
            "firewall_name": a.firewall.name if a.firewall else "",
            "firewall_id": a.firewall_id,
            "collected_at": a.collected_at.isoformat() if a.collected_at else None,
        }
        for a in assets
    ]


@router.post("/{fw_id}/refresh")
def refresh_assets(fw_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    fw = db.query(Firewall).filter(Firewall.id == fw_id).first()
    if not fw:
        raise HTTPException(status_code=404, detail="Firewall não encontrado")

    success, data = get_assets(fw.host, fw.port, fw.api_key)
    if not success:
        raise HTTPException(status_code=502, detail="Falha ao coletar assets")

    # Replace existing assets for this firewall
    db.query(Asset).filter(Asset.firewall_id == fw_id).delete()

    now = datetime.datetime.utcnow()
    for item in data:
        if not item.get("ip"):
            continue
        asset = Asset(
            firewall_id=fw_id,
            ip=item.get("ip", ""),
            mac=item.get("mac", ""),
            hostname=item.get("hostname", ""),
            interface=item.get("interface", ""),
            device_type=item.get("device_type", ""),
            collected_at=now,
        )
        db.add(asset)

    db.commit()
    count = db.query(Asset).filter(Asset.firewall_id == fw_id).count()
    return {"firewall_name": fw.name, "assets_collected": count}
