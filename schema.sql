CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT CHECK (role IN ('admin', 'teacher', 'technician')) NOT NULL
);

CREATE TABLE IF NOT EXISTS repair_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_no TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    building TEXT NOT NULL,
    room TEXT NOT NULL,
    problem_type TEXT CHECK (problem_type IN ('electrical', 'furniture', 'computer', 'aircon', 'other')) NOT NULL,
    description TEXT NOT NULL,
    urgency TEXT CHECK (urgency IN ('low', 'medium', 'high')) NOT NULL,
    status TEXT CHECK (status IN ('pending', 'accepted', 'in_progress', 'completed')) DEFAULT 'pending',
    assigned_to INTEGER,
    due_date DATE,
    completion_date DATE,
    cost REAL,
    result TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (assigned_to) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS repair_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repair_id INTEGER NOT NULL,
    image_type TEXT CHECK (image_type IN ('before', 'after')) NOT NULL,
    image_path TEXT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (repair_id) REFERENCES repair_requests(id)
);