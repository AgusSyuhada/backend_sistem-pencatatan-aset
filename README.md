# Sistem Pencatatan Aset (SIPA) API

## About

Sistem Pencatatan Aset (SIPA) adalah aplikasi backend berbasis **FastAPI** yang dirancang untuk mengelola siklus hidup aset perusahaan. Sistem ini mencakup fitur manajemen data master aset, siklus aset, integrasi OCR untuk identifikasi label aset, serta sinkronisasi dengan Google Sheets.

## Arsitektur

Project ini menggunakan **Clean Architecture** untuk memastikan pemisahan concern yang jelas, skalabilitas, dan kemudahan maintenance.

- **Routers (`app/routers`)**: Layer terluar yang menangani request HTTP dan validasi input/output (Schemas).
- **Services (`app/services`)**: Berisi business logic utama. Layer ini mengorkestrasi panggilan ke repository dan layanan eksternal (Azure, Email, Google Sheets).
- **Repositories (`app/repositories`)**: Layer akses data (DAL) yang berinteraksi langsung dengan database PostgreSQL.
- **Utils (`app/utils`)**: Fungsi utilitas umum seperti koneksi DB, security (JWT), email, dan storage.

## Tech Stack

- **Backend Framework**: Python (FastAPI)
- **Database**: PostgreSQL 15
- **Authentication**: OAuth2 dengan JWT (Bcrypt for hashing)
- **Containerization**: Docker & Docker Compose
- **Cloud Services (Azure)**:
  - Azure Blob Storage (untuk foto aset)
  - Azure Computer Vision (OCR)
  - Azure Communication Services (Email)
- **Integration**: Google Sheets API (Sync data)
- **Other Libs**: `pandas`, `pydantic`, `psycopg2`, `apscheduler`

## Quick Start

Ikuti langkah-langkah berikut untuk menjalankan aplikasi di lingkungan lokal.

### 1. Clone Repository

```bash
git clone https://github.com/AgusSyuhada/backend_sistem-pencatatan-aset.git
cd backend_sistem-pencatatan-aset
```

### 2. Konfigurasi Environment Variables

Buat file `.env` di root direktori project dan isi dengan konfigurasi berikut. Sesuaikan value dengan kredensial Anda.

```ini
# Database Config
DB_HOST=db
POSTGRES_DB=sipa_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres_password

# Security
JWT_SECRET=rahasia_super_aman_ganti_ini
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Azure Services
ACS_CONNECTION_STRING=endpoint=https://...
ACS_SENDER_ADDRESS=DoNotReply@...
BLOB_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
BLOB_CONTAINER_NAME=assets-container
AZURE_VISION_ENDPOINT=https://...
AZURE_VISION_KEY=...

# Google Sheets Integration
MASTER_SHEET_URL=https://docs.google.com/spreadsheets/d/...
CYCLE_SHEET_URL=https://docs.google.com/spreadsheets/d/...
```

### 3. Setup Database (SQL)

Buat file `init-db/init.sql` (atau jalankan query ini di tool database client Anda setelah container db berjalan). Berikut adalah skema database beserta **Data Dummy**.

```sql
-- Buat Schema
CREATE SCHEMA IF NOT EXISTS sipa;

-- 1. Tables (Lookups)
CREATE TABLE sipa.Roles (
    RoleID SERIAL PRIMARY KEY,
    RoleName VARCHAR(50) NOT NULL
);

CREATE TABLE sipa.Teams (
    TeamID SERIAL PRIMARY KEY,
    TeamName VARCHAR(100) NOT NULL
);

CREATE TABLE sipa.Manufacturers (
    ManufacturerID SERIAL PRIMARY KEY,
    ManufacturerName VARCHAR(100) NOT NULL
);

CREATE TABLE sipa.Conditions (
    ConditionID SERIAL PRIMARY KEY,
    ConditionName VARCHAR(50) NOT NULL
);

CREATE TABLE sipa.Locations (
    LocationID SERIAL PRIMARY KEY,
    SAPLocationCode VARCHAR(50),
    Area VARCHAR(100),
    Location VARCHAR(100)
);

CREATE TABLE sipa.CostCenters (
    CostCenterID SERIAL PRIMARY KEY,
    CostCenterCode VARCHAR(50) NOT NULL UNIQUE
);

-- 2. Users Table
CREATE TABLE sipa.Users (
    UserID SERIAL PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    Email VARCHAR(100) NOT NULL UNIQUE,
    Password VARCHAR(255) NOT NULL,
    RoleID INT REFERENCES sipa.Roles(RoleID),
    ProfilePictureURL TEXT,
    IsActive BOOLEAN DEFAULT TRUE,
    FailedLoginAttempts INT DEFAULT 0,
    IsLocked BOOLEAN DEFAULT FALSE,
    RefreshToken TEXT,
    RefreshTokenExpiresAt TIMESTAMP,
    LastLogin TIMESTAMP,
    LastLoginIP VARCHAR(50),
    LastLoginAgent VARCHAR(255),
    LastLoginCoordinates VARCHAR(100),
    LastLoginCity VARCHAR(100),
    LastLoginDeviceModel VARCHAR(100),
    DeviceLastUsedAt TIMESTAMP,
    LastLogout TIMESTAMP,
    PasswordResetToken VARCHAR(255),
    PasswordResetTokenExpiresAt TIMESTAMP,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Asset Master Table
CREATE TABLE sipa.MasterDataAsset (
    AssetNumber VARCHAR(50) PRIMARY KEY,
    HBM VARCHAR(50),
    SerialNumber VARCHAR(100),
    AssetName VARCHAR(255),
    ModelType VARCHAR(100),
    GPSCoordinate VARCHAR(100),
    SpecificLocation TEXT,
    Description TEXT,
    InventoryResult VARCHAR(50),
    AssetValue DECIMAL(15, 2),
    InventoryDate DATE,
    IsActive BOOLEAN DEFAULT TRUE,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CostCenterID INT REFERENCES sipa.CostCenters(CostCenterID),
    TeamID INT REFERENCES sipa.Teams(TeamID),
    ManufacturerID INT REFERENCES sipa.Manufacturers(ManufacturerID),
    ConditionID INT REFERENCES sipa.Conditions(ConditionID),
    LocationID INT REFERENCES sipa.Locations(LocationID)
);

-- 4. Asset Assignments
CREATE TABLE sipa.AssetAssignments (
    AssignmentID SERIAL PRIMARY KEY,
    AssetNumber VARCHAR(50) REFERENCES sipa.MasterDataAsset(AssetNumber),
    UserID INT REFERENCES sipa.Users(UserID),
    IsActive BOOLEAN DEFAULT TRUE,
    UNIQUE(AssetNumber, UserID, IsActive)
);

-- 5. Asset Cycle Table
CREATE TABLE sipa.AssetCycle (
    BackupID SERIAL PRIMARY KEY,
    Cycle INT NOT NULL,
    Year INT NOT NULL,
    AssetNumber VARCHAR(50), -- Tidak FK agar history tetap ada jika master dihapus
    HBM VARCHAR(50),
    SerialNumber VARCHAR(100),
    AssetName VARCHAR(255),
    ModelType VARCHAR(100),
    GPSCoordinate VARCHAR(100),
    SpecificLocation TEXT,
    Description TEXT,
    InventoryResult VARCHAR(50),
    IsCycled BOOLEAN DEFAULT FALSE,
    AssetValue DECIMAL(15, 2),
    InventoryDate DATE,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    BackupTimestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CostCenterID INT,
    TeamID INT,
    ManufacturerID INT,
    ConditionID INT,
    LocationID INT,
    UNIQUE(Year, Cycle, AssetNumber)
);

-- 6. Asset Cycle Assignments
CREATE TABLE sipa.AssetCycleAssignments (
    ID SERIAL PRIMARY KEY,
    BackupID INT REFERENCES sipa.AssetCycle(BackupID) ON DELETE CASCADE,
    UserID INT,
    IsActive BOOLEAN DEFAULT TRUE
);

-- 7. Photos
CREATE TABLE sipa.AssetPhotos (
    PhotoID SERIAL PRIMARY KEY,
    AssetNumber VARCHAR(50),
    Cycle INT,
    Year INT,
    BackupID INT,
    PhotoType VARCHAR(20), -- 'Asset', 'Code', 'Location'
    PhotoURL TEXT,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- DUMMY DATA
-- ==========================================

-- Roles
INSERT INTO sipa.Roles (RoleName) VALUES ('Admin'), ('User');

-- Teams
INSERT INTO sipa.Teams (TeamName) VALUES ('IT');

-- Manufacturers
INSERT INTO sipa.Manufacturers (ManufacturerName) VALUES ('Dell'), ('Apple'), ('HP'), ('Lenovo');

-- Conditions
INSERT INTO sipa.Conditions (ConditionName) VALUES 
('Digunakan'), ('Cadangan'), ('Rusak Ringan'), ('Rusak Berat'), ('Penghapusan'), ('Tidak Ditemukan');

-- Locations
INSERT INTO sipa.Locations (SAPLocationCode, Area, Location) VALUES 
('LOC-RIAU-01', 'Riau', 'Pekanbaru Office Lt. 1');

-- Cost Centers
INSERT INTO sipa.CostCenters (CostCenterCode) VALUES ('CC-IT-001');

-- Users
-- Note: Dalam production, gunakan bcrypt hash yang valid. Ini hanya string contoh.
INSERT INTO sipa.Users (Name, Email, Password, RoleID) VALUES 
('Admin', 'admin@example.com', '$2b$12$KkF/Iq.8/..hashedpassword..', 1),
('User', 'uuser@example.com', '$2b$12$KkF/Iq.8/..hashedpassword..', 2);

-- Master Assets
-- AssetNumber 6 digits, HBM 10 digits (last 6 digits are AssetNumber)
INSERT INTO sipa.MasterDataAsset 
(AssetNumber, HBM, AssetName, SerialNumber, ManufacturerID, TeamID, ConditionID, LocationID, CostCenterID, AssetValue) 
VALUES 
('100001', '2024100001', 'Laptop Dell XPS', 'SN123456', 1, 1, 1, 1, 1, 15000000),
('100002', '2024100002', 'Macbook Pro M1', 'SN789012', 2, 1, 1, 1, 1, 25000000);

-- Asset Assignments
INSERT INTO sipa.AssetAssignments (AssetNumber, UserID) VALUES ('100001', 2);

-- Cycle Data (Contoh untuk Tahun 2026, Cycle 1)
INSERT INTO sipa.AssetCycle 
(Cycle, Year, AssetNumber, HBM, AssetName, InventoryResult, IsCycled, BackupTimestamp)
VALUES 
(1, 2026, '100001', '2024100001', 'Laptop Dell XPS', 'Match', TRUE, NOW());

```

### 4. Menjalankan Aplikasi

Jalankan aplikasi menggunakan Docker Compose. Pastikan Docker Desktop sudah berjalan.

```bash
docker-compose up -d --build
```

- **API Documentation (Swagger UI)**: Akses di `http://localhost:8000/docs`
- **Database**: Port `5432`

## Project Structure

```
sistem_pencatatan_aset/
├── app/
│   ├── main.py              # Entry point aplikasi
│   ├── routers/             # Endpoint Controllers (API Routes)
│   ├── services/            # Business Logic
│   ├── repositories/        # Database Access Layer
│   ├── schemas/             # Pydantic Models (Validation)
│   └── utils/               # Helpers (DB, Auth, Blob, Email)
├── init-db/                 # Script inisialisasi SQL
├── docker-compose.yml       # Orchestration
├── Dockerfile               # Image definition
├── requirements.txt         # Python dependencies
└── .env                     # Environment variables
```
