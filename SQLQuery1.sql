USE CloudDB;

DROP TABLE IF EXISTS server_metrics;
DROP TABLE IF EXISTS departments;
DROP TABLE IF EXISTS server_status;
DROP TABLE IF EXISTS cloud_regions;

CREATE TABLE departments (
    dept_id INT IDENTITY(1,1) PRIMARY KEY,
    department_name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE server_status (
    status_id INT IDENTITY(1,1) PRIMARY KEY,
    status_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE cloud_regions (
    region_id INT IDENTITY(1,1) PRIMARY KEY,
    region_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE server_metrics (
    server_id VARCHAR(50) PRIMARY KEY,
    dept_id INT FOREIGN KEY REFERENCES departments(dept_id),
    status_id INT FOREIGN KEY REFERENCES server_status(status_id),
    region_id INT FOREIGN KEY REFERENCES cloud_regions(region_id),
    cpu_utilization REAL,
    monthly_cost REAL
);

