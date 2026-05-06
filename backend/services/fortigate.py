"""
FortiGate REST API client.
Uses API Token authentication (Bearer) and verify=False for self-signed certificates.
Compatible with FortiOS 6.x / 7.x.
"""
import requests
import urllib3
import json
from typing import Optional, Tuple

# Suppress SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TIMEOUT = 15


def _session(api_key: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    })
    s.verify = False
    return s


def _base(host: str, port: int) -> str:
    return f"https://{host}:{port}"


# ──────────────────────────────────────────
# CONNECTION TEST
# ──────────────────────────────────────────

def test_connection(host: str, port: int, api_key: str) -> Tuple[bool, dict]:
    """Returns (success, info_dict)"""
    try:
        s = _session(api_key)
        r = s.get(f"{_base(host, port)}/api/v2/monitor/system/status", timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        results = data.get("results", {})
        return True, {
            "serial": results.get("serial", ""),
            "model": results.get("model_name") or results.get("model", ""),
            "firmware": results.get("version", ""),
            "hostname": results.get("hostname", ""),
        }
    except requests.exceptions.ConnectionError:
        return False, {"error": "Conexão recusada. Verifique host/porta."}
    except requests.exceptions.Timeout:
        return False, {"error": "Timeout ao conectar."}
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return False, {"error": "API Key inválida (401 Unauthorized)."}
        return False, {"error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        return False, {"error": str(e)}


# ──────────────────────────────────────────
# BACKUP
# ──────────────────────────────────────────

def get_backup(host: str, port: int, api_key: str) -> Tuple[bool, bytes, str]:
    """Returns (success, file_bytes, error_message)"""
    try:
        s = _session(api_key)
        r = s.get(
            f"{_base(host, port)}/api/v2/monitor/system/config/backup",
            params={"scope": "global"},
            timeout=30,
        )
        r.raise_for_status()
        return True, r.content, ""
    except Exception as e:
        return False, b"", str(e)


# ──────────────────────────────────────────
# SECURITY RATING
# ──────────────────────────────────────────

def get_security_rating(host: str, port: int, api_key: str) -> Tuple[bool, dict]:
    """Returns (success, rating_dict)"""
    try:
        s = _session(api_key)

        # Scores overview
        r_status = s.get(
            f"{_base(host, port)}/api/v2/monitor/system/security-rating/status",
            timeout=TIMEOUT,
        )
        r_status.raise_for_status()
        status_data = r_status.json()

        # Detailed controls
        r_result = s.get(
            f"{_base(host, port)}/api/v2/monitor/system/security-rating/result",
            timeout=TIMEOUT,
        )
        r_result.raise_for_status()
        result_data = r_result.json()

        score = status_data.get("results", {}).get("score", {})
        controls = result_data.get("results", [])

        # Normalize controls list
        normalized = []
        for ctrl in controls:
            normalized.append({
                "id": ctrl.get("id", ""),
                "name": ctrl.get("name", ctrl.get("desc", "")),
                "category": ctrl.get("category", ""),
                "status": ctrl.get("status", "unknown"),
                "score": ctrl.get("score", 0),
                "recommendation": ctrl.get("recommendation", ""),
            })

        return True, {
            "posture": float(score.get("posture", score.get("value", 0))),
            "coverage": float(score.get("fabric_coverage", score.get("coverage", 0))),
            "optimization": float(score.get("optimization", 0)),
            "controls": normalized,
        }
    except Exception as e:
        return False, {"error": str(e)}


# ──────────────────────────────────────────
# ASSETS (ARP + DHCP merge)
# ──────────────────────────────────────────

def get_assets(host: str, port: int, api_key: str) -> Tuple[bool, list]:
    """Returns (success, assets_list)"""
    try:
        s = _session(api_key)
        assets = {}

        # ARP table
        try:
            r = s.get(f"{_base(host, port)}/api/v2/monitor/system/arp", timeout=TIMEOUT)
            r.raise_for_status()
            for entry in r.json().get("results", []):
                ip = entry.get("ip", "")
                if ip:
                    assets[ip] = {
                        "ip": ip,
                        "mac": entry.get("mac", ""),
                        "interface": entry.get("interface", ""),
                        "hostname": "",
                        "device_type": "",
                    }
        except Exception:
            pass

        # DHCP leases (enriches hostname)
        try:
            r = s.get(f"{_base(host, port)}/api/v2/monitor/system/dhcp", timeout=TIMEOUT)
            r.raise_for_status()
            for entry in r.json().get("results", []):
                for lease in entry.get("list", []):
                    ip = lease.get("ip", "")
                    if ip:
                        if ip not in assets:
                            assets[ip] = {
                                "ip": ip,
                                "mac": lease.get("mac", ""),
                                "interface": entry.get("interface", ""),
                                "hostname": "",
                                "device_type": "",
                            }
                        assets[ip]["hostname"] = lease.get("hostname", "")
                        if not assets[ip]["mac"]:
                            assets[ip]["mac"] = lease.get("mac", "")
        except Exception:
            pass

        return True, list(assets.values())
    except Exception as e:
        return False, [{"error": str(e)}]
