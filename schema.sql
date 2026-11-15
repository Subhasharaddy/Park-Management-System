-- ParkCare 3D database schema (MySQL 8 / MariaDB 10.5+)
-- Run with:  mysql -u root -p < schema.sql      (or use: python init_db.py)
CREATE DATABASE IF NOT EXISTS parkcare_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE parkcare_db;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(100) NOT NULL,
  email VARCHAR(150) NOT NULL UNIQUE,
  phone VARCHAR(20) NULL,
  password_hash VARCHAR(255) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS admins (
  id INT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(100) NOT NULL,
  email VARCHAR(150) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS staff (
  id INT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(100) NOT NULL,
  email VARCHAR(150) NOT NULL UNIQUE,
  phone VARCHAR(20) NULL,
  department VARCHAR(100) NULL,
  password_hash VARCHAR(255) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS parks (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  area VARCHAR(120) NULL,
  latitude DECIMAL(10,7) NOT NULL,
  longitude DECIMAL(10,7) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS complaints (
  id INT AUTO_INCREMENT PRIMARY KEY,
  complaint_code VARCHAR(20) NOT NULL UNIQUE,
  user_id INT NOT NULL,
  park_id INT NULL,
  park_other VARCHAR(150) NULL,
  title VARCHAR(150) NOT NULL,
  description TEXT NOT NULL,
  category VARCHAR(40) NOT NULL,
  latitude DECIMAL(10,7) NOT NULL,
  longitude DECIMAL(10,7) NOT NULL,
  photo_path VARCHAR(255) NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'Submitted',
  assigned_staff_id INT NULL,
  rejection_reason VARCHAR(500) NULL,
  resolution_photo_path VARCHAR(255) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  resolved_at DATETIME NULL,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (park_id) REFERENCES parks(id) ON DELETE SET NULL,
  FOREIGN KEY (assigned_staff_id) REFERENCES staff(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS complaint_updates (
  id INT AUTO_INCREMENT PRIMARY KEY,
  complaint_id INT NOT NULL,
  actor_role VARCHAR(10) NOT NULL,
  actor_name VARCHAR(100) NOT NULL,
  old_status VARCHAR(20) NULL,
  new_status VARCHAR(20) NOT NULL,
  remark VARCHAR(1000) NULL,
  photo_path VARCHAR(255) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS notifications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  complaint_id INT NULL,
  message VARCHAR(500) NOT NULL,
  is_read TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Sample parks (fictional names; coordinates are placeholders near the default map centre)
INSERT IGNORE INTO parks (name, area, latitude, longitude) VALUES
 ('Central Green Park', 'City Centre', 12.9763, 77.5929),
 ('Lakeside Garden', 'North Lake District', 13.0090, 77.5733),
 ('Heritage Botanical Garden', 'South Zone', 12.9507, 77.5848),
 ('Riverside Walk Park', 'East Bank', 12.9825, 77.6190),
 ('Sunrise Children Park', 'Residential Block A', 12.9610, 77.6010),
 ('Community Sports Park', 'West Ward', 12.9690, 77.5600);
