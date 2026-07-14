# MODULE_FF_WPC — Freight Forwarding Custom Module

Modul Odoo 18 custom untuk operasional **Freight Forwarding** Clavis Group.

---

## Prasyarat

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) terinstall
- Git

---

## Setup

**1. Clone repo**
```bash
git clone https://github.com/clavisdev9-bit/MODULE_FF_WPC.git
cd MODULE_FF_WPC
```

**2. Letakkan folder Odoo Enterprise**

Salin folder `enterprise` ke dalam direktori repo:
```
MODULE_FF_WPC/
└── enterprise/   ← letakkan di sini
```

**3. Buat file konfigurasi**
```bash
cp config/odoo.conf.example config/odoo.conf
```
Buka `config/odoo.conf` dan sesuaikan:
- `admin_passwd` — master password Odoo (bebas)
- `db_password` — password database (default: `odoo`)

**4. Jalankan Docker**
```bash
docker-compose up -d
```

**5. Akses Odoo**

Buka browser ke: **http://localhost:8066**

---
