# FortiCentralizer

Interface web centralizada para gerenciamento de múltiplos FortiGates via API REST.
Inspirada no FortiManager, mas auto-hospedada, leve e open-source.

![Stack](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square)
![Stack](https://img.shields.io/badge/Frontend-Vanilla_JS-F7DF1E?style=flat-square)
![Stack](https://img.shields.io/badge/Deploy-Docker_Compose-2496ED?style=flat-square)
![Stack](https://img.shields.io/badge/DB-SQLite-003B57?style=flat-square)

---

## Funcionalidades

| Módulo | Descrição |
|---|---|
| **Dashboard** | Visão executiva: status dos firewalls, score médio de segurança, contagem de backups e assets |
| **Backups** | Coleta e armazena configurações das caixas; download e exclusão de arquivos |
| **Security Rating** | Exibe Posture, Fabric Coverage e Optimization; drilldown por controle (pass/fail/warning) |
| **Assets** | Visão invertida global: todos os ativos descobertos (ARP + DHCP) de todas as caixas |
| **Configurações** | Cadastro de firewalls e gerenciamento de usuários do sistema |

**Certificados autoassinados**: todas as conexões usam `verify=False` — compatível com IPs internos, externos e hostnames com certificados self-signed.

---

## Requisitos

- Ubuntu 20.04+ (ou qualquer Linux com Docker)
- Docker Engine 24+
- Docker Compose v2

### Instalar Docker (Ubuntu)

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

---

## Deploy em Produção (Ubuntu)

```bash
# 1. Clonar o repositório
git clone https://github.com/SEU_USUARIO/forticentralizer.git
cd forticentralizer

# 2. (Opcional) Configurar secret key
echo "SECRET_KEY=$(openssl rand -hex 32)" > .env

# 3. Build e subir
docker compose up -d --build

# 4. Verificar
docker compose ps
docker compose logs -f
```

A aplicação ficará acessível em `http://<IP_DO_SERVIDOR>`

---

## Credenciais Padrão

| Campo | Valor |
|---|---|
| Usuário | `admin` |
| Senha | `admin123` |

> ⚠️ **Troque a senha imediatamente após o primeiro login** em Configurações → Usuários.

---

## Estrutura do Projeto

```
forticentralizer/
├── docker-compose.yml
├── .env                    # (não versionado) SECRET_KEY
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py             # Entry point FastAPI
│   ├── database.py         # SQLAlchemy + SQLite
│   ├── models.py           # Tabelas ORM
│   ├── auth.py             # JWT + bcrypt
│   ├── routers/
│   │   ├── auth_router.py
│   │   ├── firewalls.py
│   │   ├── backups.py
│   │   ├── security_rating.py
│   │   └── assets.py
│   └── services/
│       └── fortigate.py    # Cliente API FortiGate
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    └── index.html          # SPA completa (HTML + CSS + JS)
```

---

## API do FortiGate — Endpoints Utilizados

| Operação | Endpoint |
|---|---|
| Testar conexão | `GET /api/v2/monitor/system/status` |
| Backup config | `GET /api/v2/monitor/system/config/backup?scope=global` |
| Security Rating scores | `GET /api/v2/monitor/system/security-rating/status` |
| Security Rating controles | `GET /api/v2/monitor/system/security-rating/result` |
| Assets (ARP) | `GET /api/v2/monitor/system/arp` |
| Assets (DHCP) | `GET /api/v2/monitor/system/dhcp` |

### Criar API Key no FortiGate

```
System → Administrators → Create New → REST API Admin
Permissões mínimas: Read (System, Log, Monitor) + Read-Write (System Config para backup)
```

---

## Comandos Úteis

```bash
# Ver logs
docker compose logs -f backend

# Reiniciar após atualização
docker compose down && docker compose up -d --build

# Backup do banco de dados
docker cp forticentralizer-api:/data/forti_manager.db ./forti_manager_backup.db

# Acessar container do backend
docker exec -it forticentralizer-api bash
```

---

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `SECRET_KEY` | (gerado) | Chave JWT — mude em produção |
| `DATABASE_URL` | `sqlite:////data/forti_manager.db` | Path do banco |
| `BACKUP_DIR` | `/data/backups` | Diretório de backups |

---

## Licença

MIT — use, modifique e distribua livremente.
