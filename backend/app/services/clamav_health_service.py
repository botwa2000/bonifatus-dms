# backend/app/services/clamav_health_service.py
"""
Bonifatus DMS - ClamAV Health Monitoring Service
Monitors ClamAV daemon status and provides auto-restart capabilities
"""

import logging
import subprocess
import time
from typing import Dict, Optional
from datetime import datetime, timedelta
import clamd

logger = logging.getLogger(__name__)


class ClamAVHealthService:
    """
    ClamAV health monitoring and management service

    Features:
    - Health status checks
    - Auto-restart on failure
    - Connection monitoring
    - Version tracking
    """

    def __init__(self):
        self._last_check_time: Optional[datetime] = None
        self._last_status: Optional[Dict] = None
        self._restart_attempts = 0
        self._max_restart_attempts = 3
        self._restart_cooldown = timedelta(minutes=5)
        self._last_restart_attempt: Optional[datetime] = None

    async def check_health(self) -> Dict:
        """
        Check ClamAV daemon health status

        Returns:
            Dictionary with health status information
        """
        status = {
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'ClamAV',
            'status': 'unknown',
            'available': False,
            'version': None,
            'uptime': None,
            'connection_type': None,
            'database_version': None,
            'last_restart_attempt': self._last_restart_attempt.isoformat() if self._last_restart_attempt else None,
            'restart_attempts': self._restart_attempts
        }

        try:
            # Try TCP connection first
            clamav_client = None
            connection_type = None

            try:
                clamav_client = clamd.ClamdNetworkSocket(host='127.0.0.1', port=3310, timeout=5)
                ping_result = clamav_client.ping()
                connection_type = 'TCP (127.0.0.1:3310)'
                logger.debug("ClamAV health check: TCP connection successful")
            except Exception as tcp_error:
                logger.debug(f"ClamAV TCP connection failed: {tcp_error}")

                # Fallback to Unix socket
                try:
                    clamav_client = clamd.ClamdUnixSocket(timeout=5)
                    ping_result = clamav_client.ping()
                    connection_type = 'Unix Socket'
                    logger.debug("ClamAV health check: Unix socket connection successful")
                except Exception as unix_error:
                    logger.warning(f"ClamAV not available via TCP or Unix socket")
                    status['status'] = 'unavailable'
                    status['error'] = f"Connection failed: {str(unix_error)}"
                    self._last_status = status
                    self._last_check_time = datetime.utcnow()
                    return status

            if clamav_client and ping_result == 'PONG':
                status['available'] = True
                status['status'] = 'healthy'
                status['connection_type'] = connection_type

                # Get version information
                try:
                    version_info = clamav_client.version()
                    status['version'] = version_info
                    logger.debug(f"ClamAV version: {version_info}")
                except Exception as e:
                    logger.warning(f"Could not retrieve ClamAV version: {e}")

                # Get statistics
                try:
                    stats = clamav_client.stats()
                    status['stats'] = stats
                except Exception as e:
                    logger.debug(f"Could not retrieve ClamAV stats: {e}")

                # Reset restart counter on successful connection
                if self._restart_attempts > 0:
                    logger.info("ClamAV recovered - resetting restart counter")
                    self._restart_attempts = 0

            else:
                status['status'] = 'unhealthy'
                status['error'] = 'Ping failed'

        except Exception as e:
            logger.error(f"ClamAV health check error: {e}")
            status['status'] = 'error'
            status['error'] = str(e)

        self._last_status = status
        self._last_check_time = datetime.utcnow()

        return status

    async def restart_service(self) -> Dict:
        """
        Attempt to restart ClamAV daemon

        Returns:
            Dictionary with restart operation result
        """
        # Check cooldown period
        if self._last_restart_attempt:
            time_since_last = datetime.utcnow() - self._last_restart_attempt
            if time_since_last < self._restart_cooldown:
                remaining = (self._restart_cooldown - time_since_last).total_seconds()
                return {
                    'success': False,
                    'error': f'Restart cooldown active. Try again in {int(remaining)} seconds.',
                    'attempts': self._restart_attempts
                }

        # Check max attempts
        if self._restart_attempts >= self._max_restart_attempts:
            return {
                'success': False,
                'error': f'Maximum restart attempts ({self._max_restart_attempts}) reached. Manual intervention required.',
                'attempts': self._restart_attempts
            }

        self._last_restart_attempt = datetime.utcnow()
        self._restart_attempts += 1

        logger.info(f"Attempting to restart ClamAV daemon (attempt {self._restart_attempts}/{self._max_restart_attempts})")

        try:
            # Try systemctl restart (systemd)
            result = subprocess.run(
                ['systemctl', 'restart', 'clamav-daemon'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.info("ClamAV daemon restarted successfully via systemctl")

                # Wait for service to come up
                time.sleep(3)

                # Verify restart
                health = await self.check_health()

                if health['available']:
                    return {
                        'success': True,
                        'message': 'ClamAV daemon restarted successfully',
                        'method': 'systemctl',
                        'attempts': self._restart_attempts,
                        'health': health
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Service restarted but health check failed',
                        'attempts': self._restart_attempts,
                        'health': health
                    }
            else:
                error_msg = result.stderr.strip()
                logger.error(f"Systemctl restart failed: {error_msg}")

                # Try alternative restart methods
                return await self._try_alternative_restart()

        except subprocess.TimeoutExpired:
            logger.error("ClamAV restart timed out")
            return {
                'success': False,
                'error': 'Restart command timed out',
                'attempts': self._restart_attempts
            }
        except FileNotFoundError:
            logger.warning("systemctl not found, trying alternative methods")
            return await self._try_alternative_restart()
        except Exception as e:
            logger.error(f"ClamAV restart error: {e}")
            return {
                'success': False,
                'error': str(e),
                'attempts': self._restart_attempts
            }

    async def _try_alternative_restart(self) -> Dict:
        """Try alternative restart methods"""

        # Try service command
        try:
            result = subprocess.run(
                ['service', 'clamav-daemon', 'restart'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.info("ClamAV daemon restarted via service command")
                time.sleep(3)
                health = await self.check_health()

                return {
                    'success': health['available'],
                    'message': 'Restarted via service command',
                    'method': 'service',
                    'attempts': self._restart_attempts,
                    'health': health
                }
        except Exception as e:
            logger.debug(f"Service command failed: {e}")

        # Try direct clamd restart
        try:
            result = subprocess.run(
                ['clamd'],
                capture_output=True,
                text=True,
                timeout=5
            )
            logger.info("Attempted direct clamd start")
            time.sleep(3)
            health = await self.check_health()

            return {
                'success': health['available'],
                'message': 'Attempted direct clamd start',
                'method': 'direct',
                'attempts': self._restart_attempts,
                'health': health
            }
        except Exception as e:
            logger.error(f"Direct clamd start failed: {e}")

        return {
            'success': False,
            'error': 'All restart methods failed. Manual intervention required.',
            'attempts': self._restart_attempts
        }

    def get_last_status(self) -> Optional[Dict]:
        """Get cached health status without performing new check"""
        return self._last_status

    def reset_restart_counter(self):
        """Manually reset restart attempt counter"""
        self._restart_attempts = 0
        logger.info("ClamAV restart counter manually reset")


# Global service instance
clamav_health_service = ClamAVHealthService()
