USE CloudDB;

CREATE TABLE server_metrics (
    server_id VARCHAR(50) PRIMARY KEY,
    department VARCHAR(100),
    cpu_utilization REAL,
    monthly_cost REAL,
    status VARCHAR(50)
);

