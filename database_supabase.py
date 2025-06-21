import os
import logging
from typing import Optional, Dict, List, Any
from supabase import create_client, Client
from datetime import datetime
import json

logger = logging.getLogger('EngagementBot')

class SupabaseDatabase:
    """Database manager using Supabase PostgreSQL"""
    
    def __init__(self):
        self.supabase: Client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Supabase client"""
        try:
            url = os.getenv('SUPABASE_URL')
            key = os.getenv('SUPABASE_ANON_KEY')
            
            if not url or not key:
                logger.error("Supabase credentials not found in environment variables")
                return
            
            self.supabase = create_client(url, key)
            logger.info("Supabase client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}", exc_info=True)
    
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self.supabase is not None
    
    # === USER MANAGEMENT ===
    
    def get_user_data(self, user_id: str) -> Dict:
        """Get user data"""
        try:
            result = self.supabase.table('users').select('*').eq('user_id', user_id).execute()
            
            if result.data:
                return result.data[0]
            else:
                # Create new user
                new_user = {
                    'user_id': user_id,
                    'points': 0
                }
                self.supabase.table('users').insert(new_user).execute()
                return new_user
                
        except Exception as e:
            logger.error(f"Error getting user data: {e}", exc_info=True)
            return {'user_id': user_id, 'points': 0}
    
    def add_points(self, user_id: str, points: int):
        """Add points to user"""
        try:
            # Upsert user with points increment
            result = self.supabase.rpc('add_user_points', {
                'p_user_id': user_id,
                'p_points': points
            }).execute()
            
            if result.data is None:
                # Fallback method
                current_user = self.get_user_data(user_id)
                new_points = current_user['points'] + points
                self.supabase.table('users').upsert({
                    'user_id': user_id,
                    'points': new_points,
                    'updated_at': datetime.now().isoformat()
                }).execute()
            
            logger.info(f"Added {points} points to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error adding points: {e}", exc_info=True)
    
    def remove_points(self, user_id: str, points: int) -> bool:
        """Remove points from user"""
        try:
            current_user = self.get_user_data(user_id)
            
            if current_user['points'] < points:
                return False
            
            new_points = current_user['points'] - points
            self.supabase.table('users').update({
                'points': new_points,
                'updated_at': datetime.now().isoformat()
            }).eq('user_id', user_id).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error removing points: {e}", exc_info=True)
            return False
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get points leaderboard"""
        try:
            result = self.supabase.table('users').select('*').order('points', desc=True).limit(limit).execute()
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}", exc_info=True)
            return []
    
    # === GANG MANAGEMENT ===
    
    def create_gang(self, name: str, boss_id: str, description: str = "") -> bool:
        """Create a new gang"""
        try:
            gang_data = {
                'name': name,
                'description': description,
                'boss_id': boss_id,
                'vault_points': 0,
                'reputation': 0,
                'territory_count': 0
            }
            
            result = self.supabase.table('gangs').insert(gang_data).execute()
            
            if result.data:
                gang_id = result.data[0]['id']
                
                # Add boss as member
                self.supabase.table('gang_members').insert({
                    'gang_id': gang_id,
                    'user_id': boss_id,
                    'rank': 'boss'
                }).execute()
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error creating gang: {e}", exc_info=True)
            return False
    
    def get_gang_by_name(self, name: str) -> Optional[Dict]:
        """Get gang by name"""
        try:
            result = self.supabase.table('gangs').select('*').eq('name', name).execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error getting gang by name: {e}", exc_info=True)
            return None
    
    def get_user_gang(self, user_id: str) -> Optional[str]:
        """Get user's gang ID"""
        try:
            result = self.supabase.table('gang_members').select('gang_id').eq('user_id', user_id).execute()
            return result.data[0]['gang_id'] if result.data else None
            
        except Exception as e:
            logger.error(f"Error getting user gang: {e}", exc_info=True)
            return None
    
    # === TERRITORY MANAGEMENT ===
    
    def get_all_territories(self) -> List[Dict]:
        """Get all territories"""
        try:
            result = self.supabase.table('territories').select('*').execute()
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting territories: {e}", exc_info=True)
            return []
    
    def claim_territory(self, territory_id: str, gang_id: str) -> bool:
        """Claim a territory for a gang"""
        try:
            result = self.supabase.table('territories').update({
                'controlled_by': gang_id,
                'controlled_since': datetime.now().isoformat()
            }).eq('id', territory_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error claiming territory: {e}", exc_info=True)
            return False
    
    # === COOLDOWNS & SESSIONS ===
    
    def set_cooldown(self, table_name: str, user_id: str, cooldown_time: float):
        """Set user cooldown (using JSON storage for backwards compatibility)"""
        try:
            # For now, we'll store cooldowns in a JSON column
            # In production, you'd want separate tables for each type
            self.supabase.table('user_cooldowns').upsert({
                'user_id': user_id,
                'cooldown_type': table_name,
                'cooldown_until': cooldown_time,
                'updated_at': datetime.now().isoformat()
            }).execute()
            
        except Exception as e:
            logger.error(f"Error setting cooldown: {e}", exc_info=True)
    
    def get_cooldown(self, table_name: str, user_id: str) -> Optional[float]:
        """Get user cooldown"""
        try:
            result = self.supabase.table('user_cooldowns').select('cooldown_until').eq('user_id', user_id).eq('cooldown_type', table_name).execute()
            
            if result.data:
                return result.data[0]['cooldown_until']
            return None
            
        except Exception as e:
            logger.error(f"Error getting cooldown: {e}", exc_info=True)
            return None
    
    # === MIGRATION HELPER ===
    
    def migrate_from_json(self, json_file_path: str):
        """Migrate data from JSON file to Supabase"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info("Starting migration from JSON to Supabase...")
            
            # Migrate users
            if 'users' in data:
                for user_id, user_data in data['users'].items():
                    self.supabase.table('users').upsert({
                        'user_id': user_id,
                        'points': user_data.get('points', 0)
                    }).execute()
                logger.info(f"Migrated {len(data['users'])} users")
            
            # Migrate gangs (if any exist in old format)
            if 'gangs' in data and data['gangs']:
                for gang_id, gang_data in data['gangs'].items():
                    self.create_gang(
                        gang_data['name'],
                        gang_data['boss_id'],
                        gang_data.get('description', '')
                    )
                logger.info(f"Migrated {len(data['gangs'])} gangs")
            
            logger.info("Migration completed successfully!")
            
        except Exception as e:
            logger.error(f"Error during migration: {e}", exc_info=True)

# === SQL FUNCTIONS (à exécuter dans Supabase) ===
SQL_FUNCTIONS = """
-- Function to add points atomically
CREATE OR REPLACE FUNCTION add_user_points(p_user_id TEXT, p_points INTEGER)
RETURNS VOID AS $$
BEGIN
    INSERT INTO users (user_id, points, updated_at)
    VALUES (p_user_id, p_points, NOW())
    ON CONFLICT (user_id)
    DO UPDATE SET 
        points = users.points + p_points,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- Function to get gang with members
CREATE OR REPLACE FUNCTION get_gang_with_members(p_gang_id UUID)
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_build_object(
        'gang', row_to_json(g),
        'members', COALESCE(
            (SELECT json_agg(
                json_build_object(
                    'user_id', gm.user_id,
                    'rank', gm.rank,
                    'joined_at', gm.joined_at
                )
            ) FROM gang_members gm WHERE gm.gang_id = p_gang_id),
            '[]'::json
        )
    ) INTO result
    FROM gangs g
    WHERE g.id = p_gang_id;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;
"""