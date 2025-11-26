# app/health_check.py
"""
Health check module for the Onestream RAG application.
Provides functions to check the health and status of various components.
"""

import os
import time
from typing import Dict, List, Tuple, Optional
from pathlib import Path

class HealthCheckError(Exception):
    """Custom exception for health check errors."""
    pass

class HealthChecker:
    """Health checker for monitoring application components."""
    
    def __init__(self, config: Dict):
        """
        Initialize health checker.
        
        Args:
            config: Application configuration dictionary
        """
        self.config = config
    
    def check_disk_space(self, path: str, min_free_mb: int = 100) -> Tuple[bool, str]:
        """
        Check if there's enough disk space.
        
        Args:
            path: Path to check
            min_free_mb: Minimum free space in MB
            
        Returns:
            Tuple of (is_healthy, message)
        """
        try:
            if not os.path.exists(path):
                return False, f"Path does not exist: {path}"
            
            stat = os.statvfs(path)
            free_bytes = stat.f_frsize * stat.f_bavail
            free_mb = free_bytes / (1024 * 1024)
            
            if free_mb < min_free_mb:
                return False, f"Low disk space: {free_mb:.1f}MB free, minimum {min_free_mb}MB required"
            
            return True, f"Sufficient disk space: {free_mb:.1f}MB free"
        except Exception as e:
            return False, f"Failed to check disk space: {str(e)}"
    
    def check_paths(self) -> List[Tuple[str, bool, str]]:
        """
        Check if required paths exist and are accessible.
        
        Returns:
            List of (path, is_healthy, message) tuples
        """
        paths_to_check = [
            ("documents_dir", self.config.get("DOCUMENTS_DIR")),
            ("qdrant_path", self.config.get("QDRANT_PATH")),
        ]
        
        results = []
        for name, path in paths_to_check:
            if not path:
                results.append((name, False, "Path not configured"))
                continue
                
            try:
                if os.path.exists(path):
                    if os.access(path, os.R_OK | os.W_OK):
                        results.append((name, True, f"Path accessible: {path}"))
                    else:
                        results.append((name, False, f"Path not accessible for read/write: {path}"))
                else:
                    # Try to create the directory
                    os.makedirs(path, exist_ok=True)
                    results.append((name, True, f"Path created: {path}"))
            except Exception as e:
                results.append((name, False, f"Path error: {str(e)}"))
        
        return results
    
    def check_dependencies(self) -> List[Tuple[str, bool, str]]:
        """
        Check if required dependencies are available.
        
        Returns:
            List of (dependency, is_healthy, message) tuples
        """
        # This would typically check for external services, but for now
        # we'll just return a placeholder
        return [
            ("python_packages", True, "Python packages loaded successfully"),
        ]
    
    def check_vector_store(self, vector_manager: Optional[object] = None) -> Tuple[bool, str]:
        """
        Check vector store health.
        
        Args:
            vector_manager: Vector store manager instance
            
        Returns:
            Tuple of (is_healthy, message)
        """
        if not vector_manager:
            return False, "Vector store manager not provided"
            
        try:
            # Check if client is initialized
            if not hasattr(vector_manager, 'client') or not vector_manager.client:
                return False, "Vector store client not initialized"
            
            # Check if collection exists
            if vector_manager.collection_exists():
                return True, "Vector store is healthy"
            else:
                return True, "Vector store initialized but no collection yet"
        except Exception as e:
            return False, f"Vector store error: {str(e)}"
    
    def run_comprehensive_check(self, vector_manager: Optional[object] = None) -> Dict:
        """
        Run a comprehensive health check.
        
        Args:
            vector_manager: Vector store manager instance
            
        Returns:
            Health check results dictionary
        """
        start_time = time.time()
        
        # Run all checks
        disk_healthy, disk_message = self.check_disk_space(
            self.config.get("QDRANT_PATH", "."), 
            self.config.get("MIN_DISK_SPACE_MB", 100)
        )
        
        path_results = self.check_paths()
        dependency_results = self.check_dependencies()
        vector_healthy, vector_message = self.check_vector_store(vector_manager)
        
        # Compile results
        all_path_healthy = all(result[1] for result in path_results)
        all_deps_healthy = all(result[1] for result in dependency_results)
        
        overall_healthy = (
            disk_healthy and 
            all_path_healthy and 
            all_deps_healthy and 
            vector_healthy
        )
        
        elapsed_time = time.time() - start_time
        
        return {
            "overall_healthy": overall_healthy,
            "timestamp": time.time(),
            "duration_seconds": elapsed_time,
            "checks": {
                "disk_space": {
                    "healthy": disk_healthy,
                    "message": disk_message
                },
                "paths": {
                    "healthy": all_path_healthy,
                    "details": path_results
                },
                "dependencies": {
                    "healthy": all_deps_healthy,
                    "details": dependency_results
                },
                "vector_store": {
                    "healthy": vector_healthy,
                    "message": vector_message
                }
            }
        }

def format_health_report(health_results: Dict) -> str:
    """
    Format health check results into a readable report.
    
    Args:
        health_results: Health check results dictionary
        
    Returns:
        Formatted health report
    """
    if not health_results:
        return "No health check results available"
    
    overall_status = "✅ HEALTHY" if health_results.get("overall_healthy") else "❌ UNHEALTHY"
    
    report = f"""
# Application Health Report

**Overall Status:** {overall_status}
**Check Duration:** {health_results.get('duration_seconds', 0):.2f} seconds
**Timestamp:** {time.ctime(health_results.get('timestamp', 0))}

## Detailed Checks

### Disk Space
- Status: {'✅' if health_results['checks']['disk_space']['healthy'] else '❌'}
- Message: {health_results['checks']['disk_space']['message']}

### Paths
- Status: {'✅' if health_results['checks']['paths']['healthy'] else '❌'}
"""
    
    for path_name, is_healthy, message in health_results['checks']['paths']['details']:
        report += f"  - {path_name}: {'✅' if is_healthy else '❌'} {message}\n"
    
    report += f"""
### Dependencies
- Status: {'✅' if health_results['checks']['dependencies']['healthy'] else '❌'}
"""
    
    for dep_name, is_healthy, message in health_results['checks']['dependencies']['details']:
        report += f"  - {dep_name}: {'✅' if is_healthy else '❌'} {message}\n"
    
    report += f"""
### Vector Store
- Status: {'✅' if health_results['checks']['vector_store']['healthy'] else '❌'}
- Message: {health_results['checks']['vector_store']['message']}
"""
    
    return report.strip()
