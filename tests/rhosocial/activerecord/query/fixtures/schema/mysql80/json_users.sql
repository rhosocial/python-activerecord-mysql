CREATE TABLE json_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    age INT,
    settings TEXT,
    tags TEXT,
    profile TEXT,
    roles TEXT,
    scores TEXT,
    subscription TEXT,
    preferences TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);