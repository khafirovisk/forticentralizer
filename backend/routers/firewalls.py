from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import datetime
from database import get_db
from models import Firewall
from auth import get_current_user
from services.fortigate import test_connection

router = APIRouter(prefix="/firewalls", tags=["firewalls"])


class FirewallCreate(BaseModel):
    name: str
    host: str
    port: int = 443
    api_key: str


class FirewallUpdate(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    api_key: Optional[str] = None


def fw_to_dict(fw: Firewall) -> dict:
    return {
        "id": fw.id,
        "name": fw.name,
        "host": fw.host,
        "port": fw.port,
        "serial": fw.serial,
        "model": fw.model,
        "firmware": fw.firmware,
        "status": fw.status,
        "last_seen": fw.last_seen.isoformat() if fw.last_seen else None,
        "created_at": fw.created_at.isoformat() if fw.created_at else None,
    }


@router.get("")
def list_firewalls(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return [fw_to_dict(fw) for fw in db.query(Firewall).all()]


@router.post("")
def create_firewall(req: FirewallCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if db.query(Firewall).filter(Firewall.name == req.name).first():
        raise HTTPException(status_code=400, detail="Já existe um firewall com esse nome")
    fw = Firewall(**req.dict())
    db.add(fw)
    db.commit()
    db.refresh(fw)
    return fw_to_dict(fw)


@router.put("/{fw_id}")
def update_firewall(fw_id: int, req: FirewallUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    fw = db.query(Firewall).filter(Firewall.id == fw_id).first()
    if not fw:
        raise HTTPException(status_code=404, detail="Firewall não encontrado")
    for k, v in req.dict(exclude_none=True).items():
        setattr(fw, k, v)
    db.commit()
    db.refresh(fw)
    return fw_to_dict(fw)


@router.delete("/{fw_id}")
def delete_firewall(fw_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    fw = db.query(Firewall).filter(Firewall.id == fw_id).first()
    if not fw:
        raise HTTPException(status_code=404, detail="Firewall não encontrado")
    db.delete(fw)
    db.commit()
    return {"ok": True}


@router.post("/{fw_id}/test")
def test_firewall(fw_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    fw = db.query(Firewall).filter(Firewall.id == fw_id).first()
    if not fw:
        raise HTTPException(status_code=404, detail="Firewall não encontrado")

    success, info = test_connection(fw.host, fw.port, fw.api_key)

    if success:
        fw.status = "online"
        fw.last_seen = datetime.datetime.utcnow()
        if info.get("serial"):
            fw.serial = info["serial"]
        if info.get("model"):
            fw.model = info["model"]
        if info.get("firmware"):
            fw.firmware = info["firmware"]
    else:
        fw.status = "offline"

    db.commit()
    return {"success": success, "info": info, "status": fw.status}
