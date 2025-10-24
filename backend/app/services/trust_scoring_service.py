# backend/app/services/trust_scoring_service.py
"""
Trust scoring service for behavioral security analysis
Calculates user trust based on account age, activity patterns, and behavior
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.connection import db_manager

logger = logging.getLogger(__name__)


class TrustScoringService:
    """Calculate user trust scores based on behavioral patterns"""
    
    # Trust score thresholds
    HIGH_TRUST = 0.7
    MEDIUM_TRUST = 0.5
    LOW_TRUST = 0.3
    
    # Time windows for velocity checks
    VELOCITY_WINDOW_MINUTES = 5
    VELOCITY_WINDOW_HOUR = 60
    
    def __init__(self):
        self._cache = {}
        self._cache_ttl = timedelta(minutes=5)
    
    async def calculate_trust_score(
        self,
        user_id: str,
        ip_address: Optional[str] = None,
        session: Optional[Session] = None
    ) -> float:
        """
        Calculate trust score (0.0 to 1.0) based on user behavior
        Higher score = more trusted, lower score = more scrutiny needed
        """
        close_session = False
        if session is None:
            session = db_manager.session_local()
            close_session = True
        
        try:
            # Check cache first
            cache_key = f"{user_id}:{ip_address}"
            if cache_key in self._cache:
                cached_score, cached_time = self._cache[cache_key]
                if datetime.now(timezone.utc) - cached_time < self._cache_ttl:
                    return cached_score
            
            # Start with neutral baseline
            score = 0.5
            
            # Get user information
            user_info = await self._get_user_info(user_id, session)
            if not user_info:
                return 0.3  # Low trust for unknown user
            
            # Factor 1: Account age (0 to +0.15)
            account_age_score = await self._score_account_age(user_info)
            score += account_age_score

            # Factor 2: Upload history (0 to +0.2)
            upload_history_score = await self._score_upload_history(user_id, session)
            score += upload_history_score
            
            # Factor 4: Upload velocity (-0.3 to 0)
            velocity_penalty = await self._check_upload_velocity(user_id, session)
            score += velocity_penalty
            
            # Factor 5: File diversity (-0.2 to 0)
            diversity_penalty = await self._check_file_diversity(user_id, session)
            score += diversity_penalty
            
            # Factor 6: Time patterns (-0.1 to 0)
            time_penalty = await self._check_time_patterns(user_id, session)
            score += time_penalty
            
            # Factor 7: IP address consistency (-0.1 to +0.05)
            if ip_address:
                ip_score = await self._score_ip_consistency(user_id, ip_address, session)
                score += ip_score
            
            # Clamp score to valid range
            final_score = max(0.0, min(1.0, score))
            
            # Cache result
            self._cache[cache_key] = (final_score, datetime.now(timezone.utc))
            
            # Log low trust scores
            if final_score < self.LOW_TRUST:
                logger.warning(
                    f"Low trust score for user {user_id}: {final_score:.2f}"
                )
            
            return final_score
            
        except Exception as e:
            logger.error(f"Trust score calculation error: {e}")
            return 0.5  # Return neutral on error
        finally:
            if close_session:
                session.close()
    
    async def _get_user_info(self, user_id: str, session: Session) -> Optional[Dict]:
        """Get basic user information"""
        result = session.execute(
            text("""
                SELECT
                    email,
                    created_at,
                    tier,
                    is_active
                FROM users
                WHERE id = :user_id
            """),
            {'user_id': user_id}
        ).first()

        if not result:
            return None

        return {
            'email': result[0],
            'created_at': result[1],
            'tier': result[2],
            'is_active': result[3]
        }
    
    async def _score_account_age(self, user_info: Dict) -> float:
        """Score based on account age (older = more trusted)"""
        created_at = user_info.get('created_at')
        if not created_at:
            return 0.0

        account_age = datetime.now(timezone.utc) - created_at
        
        if account_age.days >= 90:
            return 0.15  # 3+ months: high trust
        elif account_age.days >= 30:
            return 0.10  # 1-3 months: good trust
        elif account_age.days >= 7:
            return 0.05  # 1 week to 1 month: medium trust
        else:
            return 0.0  # New account: neutral
    
    async def _score_upload_history(self, user_id: str, session: Session) -> float:
        """Score based on successful upload history"""
        result = session.execute(
            text("""
                SELECT COUNT(*) as upload_count
                FROM documents
                WHERE user_id = :user_id
                AND is_deleted = false
            """),
            {'user_id': user_id}
        ).first()
        
        upload_count = result[0] if result else 0
        
        if upload_count >= 100:
            return 0.20  # Heavy user: high trust
        elif upload_count >= 50:
            return 0.15  # Regular user
        elif upload_count >= 10:
            return 0.10  # Established user
        elif upload_count >= 1:
            return 0.05  # Has uploads
        else:
            return 0.0  # No uploads yet
    
    async def _check_upload_velocity(self, user_id: str, session: Session) -> float:
        """Check for suspicious upload velocity spikes"""
        now = datetime.utcnow()
        
        # Check uploads in last 5 minutes
        recent_result = session.execute(
            text("""
                SELECT COUNT(*) as recent_count
                FROM documents
                WHERE user_id = :user_id
                AND created_at >= :time_threshold
            """),
            {
                'user_id': user_id,
                'time_threshold': now - timedelta(minutes=self.VELOCITY_WINDOW_MINUTES)
            }
        ).first()
        
        recent_count = recent_result[0] if recent_result else 0
        
        # Check uploads in last hour
        hourly_result = session.execute(
            text("""
                SELECT COUNT(*) as hourly_count
                FROM documents
                WHERE user_id = :user_id
                AND created_at >= :time_threshold
            """),
            {
                'user_id': user_id,
                'time_threshold': now - timedelta(minutes=self.VELOCITY_WINDOW_HOUR)
            }
        ).first()
        
        hourly_count = hourly_result[0] if hourly_result else 0
        
        # Penalize suspicious velocity
        penalty = 0.0
        
        if recent_count > 20:  # >20 uploads in 5 minutes
            penalty -= 0.3
        elif recent_count > 10:  # >10 uploads in 5 minutes
            penalty -= 0.2
        elif hourly_count > 100:  # >100 uploads in 1 hour
            penalty -= 0.15
        elif hourly_count > 50:  # >50 uploads in 1 hour
            penalty -= 0.1
        
        return penalty
    
    async def _check_file_diversity(self, user_id: str, session: Session) -> float:
        """Check if user is uploading same file repeatedly"""
        now = datetime.utcnow()
        
        result = session.execute(
            text("""
                SELECT file_hash, COUNT(*) as duplicate_count
                FROM documents
                WHERE user_id = :user_id
                AND created_at >= :time_threshold
                GROUP BY file_hash
                HAVING COUNT(*) > 5
                ORDER BY COUNT(*) DESC
                LIMIT 1
            """),
            {
                'user_id': user_id,
                'time_threshold': now - timedelta(hours=24)
            }
        ).first()
        
        if result:
            duplicate_count = result[1]
            if duplicate_count > 20:
                return -0.2  # Same file 20+ times: very suspicious
            elif duplicate_count > 10:
                return -0.15  # Same file 10+ times: suspicious
            else:
                return -0.05  # Some duplication: slightly suspicious
        
        return 0.0  # Good diversity
    
    async def _check_time_patterns(self, user_id: str, session: Session) -> float:
        """Check for unusual time patterns (e.g., bot activity)"""
        now = datetime.utcnow()
        current_hour = now.hour
        
        # Check if recent activity is during unusual hours (2 AM - 5 AM)
        if 2 <= current_hour <= 5:
            recent_result = session.execute(
                text("""
                    SELECT COUNT(*) as night_count
                    FROM documents
                    WHERE user_id = :user_id
                    AND created_at >= :time_threshold
                """),
                {
                    'user_id': user_id,
                    'time_threshold': now - timedelta(hours=1)
                }
            ).first()
            
            night_count = recent_result[0] if recent_result else 0
            
            if night_count > 10:
                return -0.1  # Heavy activity during unusual hours
        
        return 0.0  # Normal time pattern
    
    async def _score_ip_consistency(
        self,
        user_id: str,
        current_ip: str,
        session: Session
    ) -> float:
        """Score based on IP address consistency"""
        # Check if user has used this IP before
        result = session.execute(
            text("""
                SELECT COUNT(DISTINCT ip_address) as ip_count
                FROM audit_logs
                WHERE user_id = :user_id
                AND action = 'upload_document'
                AND created_at >= :time_threshold
            """),
            {
                'user_id': user_id,
                'time_threshold': datetime.utcnow() - timedelta(days=30)
            }
        ).first()
        
        ip_count = result[0] if result else 0
        
        if ip_count == 1:
            return 0.05  # Consistent IP: trusted
        elif ip_count <= 3:
            return 0.0  # A few IPs: normal
        elif ip_count <= 10:
            return -0.05  # Many IPs: slightly suspicious
        else:
            return -0.1  # Too many IPs: suspicious
    
    def clear_cache(self, user_id: Optional[str] = None):
        """Clear trust score cache for user or all users"""
        if user_id:
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(user_id)]
            for key in keys_to_remove:
                del self._cache[key]
        else:
            self._cache.clear()


# Global service instance
trust_scoring_service = TrustScoringService()