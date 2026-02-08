-- Create users table
CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY,
  username TEXT,
  points BIGINT DEFAULT 0,
  last_work DOUBLE PRECISION DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Create user_cooldowns table
CREATE TABLE IF NOT EXISTS user_cooldowns (
  user_id TEXT NOT NULL,
  cooldown_type TEXT NOT NULL,
  cooldown_until DOUBLE PRECISION,
  PRIMARY KEY (user_id, cooldown_type)
);

-- Create command_usage table
CREATE TABLE IF NOT EXISTS command_usage (
  user_id TEXT NOT NULL,
  command_name TEXT NOT NULL,
  date TEXT NOT NULL,
  usage_count INTEGER DEFAULT 1,
  PRIMARY KEY (user_id, command_name, date)
);

-- Create gangs table
CREATE TABLE IF NOT EXISTS gangs (
  gang_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  leader_id TEXT NOT NULL,
  founded_at TIMESTAMP DEFAULT NOW(),
  points BIGINT DEFAULT 0,
  territory TEXT,
  war_status TEXT
);

-- Create gang_members table
CREATE TABLE IF NOT EXISTS gang_members (
  user_id TEXT NOT NULL,
  gang_id TEXT NOT NULL,
  role TEXT DEFAULT 'member',
  joined_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (user_id, gang_id),
  FOREIGN KEY (gang_id) REFERENCES gangs(gang_id)
);

-- Create voice_sessions table
CREATE TABLE IF NOT EXISTS voice_sessions (
  user_id TEXT PRIMARY KEY,
  start_time DOUBLE PRECISION,
  event_name TEXT
);

-- Enable RLS (Row Level Security) - optional
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_cooldowns ENABLE ROW LEVEL SECURITY;
ALTER TABLE command_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE gangs ENABLE ROW LEVEL SECURITY;
ALTER TABLE gang_members ENABLE ROW LEVEL SECURITY;

-- Create policies to allow anonymous access (for testing)
CREATE POLICY "Allow anonymous read" ON users FOR SELECT USING (true);
CREATE POLICY "Allow anonymous insert" ON users FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow anonymous update" ON users FOR UPDATE USING (true);
CREATE POLICY "Allow anonymous delete" ON users FOR DELETE USING (true);

CREATE POLICY "Allow anonymous read" ON user_cooldowns FOR SELECT USING (true);
CREATE POLICY "Allow anonymous insert" ON user_cooldowns FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow anonymous update" ON user_cooldowns FOR UPDATE USING (true);
CREATE POLICY "Allow anonymous delete" ON user_cooldowns FOR DELETE USING (true);

CREATE POLICY "Allow anonymous read" ON command_usage FOR SELECT USING (true);
CREATE POLICY "Allow anonymous insert" ON command_usage FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow anonymous update" ON command_usage FOR UPDATE USING (true);
CREATE POLICY "Allow anonymous delete" ON command_usage FOR DELETE USING (true);

CREATE POLICY "Allow anonymous read" ON gangs FOR SELECT USING (true);
CREATE POLICY "Allow anonymous insert" ON gangs FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow anonymous update" ON gangs FOR UPDATE USING (true);
CREATE POLICY "Allow anonymous delete" ON gangs FOR DELETE USING (true);

CREATE POLICY "Allow anonymous read" ON gang_members FOR SELECT USING (true);
CREATE POLICY "Allow anonymous insert" ON gang_members FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow anonymous update" ON gang_members FOR UPDATE USING (true);
CREATE POLICY "Allow anonymous delete" ON gang_members FOR DELETE USING (true);

CREATE POLICY "Allow anonymous read" ON voice_sessions FOR SELECT USING (true);
CREATE POLICY "Allow anonymous insert" ON voice_sessions FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow anonymous update" ON voice_sessions FOR UPDATE USING (true);
CREATE POLICY "Allow anonymous delete" ON voice_sessions FOR DELETE USING (true);
