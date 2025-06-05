CREATE DATABASE IF NOT EXISTS goethe_alarm_db;
USE goethe_alarm_db;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    plan_days INT,
    start_date DATETIME,
    end_date DATETIME,
    devices TEXT,
    is_active BOOLEAN DEFAULT TRUE
);
