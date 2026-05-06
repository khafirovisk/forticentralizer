from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import datetime, os
from database import get_db
from models import Firewall, Backup
from auth import get_current_user
from services.fortigate import get_backup

router = APIRouter(prefix="/backups", tags=["backups"])

BACKUP_DIR = os.getenv("BACKUP_DIR", "/data/backups")


def backup_to_dict(b: Backup, fw_name: str = "") -> dict:
    return {
        "id": b.id,
        "firewall_id": b.firewall_id,
        "firewall_name": fw_name or (b.firewall.name if b.firewall else ""),
        "filename": b.filename,
        "file_size": b.file_size,
        "created_at": b.created_at.isoformat() if b.created_at else None,
    }


@router.get("")
def list_all_backups(db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Latest backup per firewall for the dashboard/backup list view"""
    firewalls = db.query(Firewall).all()
    result = []
    for fw in firewalls:
        latest = (
            db.query(Backup)
            .filter(Backup.firewall_id == fw.id)
            .order_by(Backup.created_at.desc())
            .first()
        )
        result.append({
            "firewall_id": fw.id,
            "firewall_name": fw.name,
            "serial": fw.serial,
            "status": fw.status,
            "last_backup": latest.created_at.isoformat() if latest else None,
            "backup_count": db.query(Backup).filter(Backup.firewall_id == fw.id).count(),
        })
    return result


@router.get("/firewall/{fw_id}")
def list_firewall_backups(fw_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    fw = db.query(Firewall).filter(Firewall.id == fw_id).first()
    if not fw:
        raise HTTPException(status_code=404, detail="Firewall não encontrado")
    backups = (
        db.query(Backup)
        .filter(Backup.firewall_id == fw_id)
        .order_by(Backup.created_at.desc())
        .all()
    )
    return [backup_to_dict(b, fw.name) for b in backups]


@router.post("/firewall/{fw_id}")
def run_backup(fw_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    fw = db.query(Firewall).filter(Firewall.id == fw_id).first()
    if not fw:
        raise HTTPException(status_code=404, detail="Firewall não encontrado")

    success, data, error = get_backup(fw.host, fw.port, fw.api_key)
    if not success:
        raise HTTPException(status_code=502, detail=f"Falha ao coletar backup: {error}")

    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{fw.name}_{ts}.conf"
    filepath = os.path.join(BACKUP_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(data)

    backup = Backup(
        firewall_id=fw.id,
        filename=filename,
        file_path=filepath,
        file_size=len(data),
    )
    db.add(backup)
    db.commit()
    db.refresh(backup)
    return backup_to_dict(backup, fw.name)


@router.get("/{backup_id}/download")
def download_backup(backup_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    b = db.query(Backup).filter(Backup.id == backup_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Backup não encontrado")
    if not os.path.exists(b.file_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no servidor")
    return FileResponse(b.file_path, filename=b.filename, media_type="application/octet-stream")


@router.delete("/{backup_id}")
def delete_backup(backup_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    b = db.query(Backup).filter(Backup.id == backup_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Backup não encontrado")
    if os.path.exists(b.file_path):
        os.remove(b.file_path)
    db.delete(b)
    db.commit()
    return {"ok": True}
