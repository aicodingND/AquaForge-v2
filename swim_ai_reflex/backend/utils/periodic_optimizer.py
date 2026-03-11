"""
Periodic Performance Optimizer
Automatically runs optimizations every N minutes to prevent lag buildup
"""

import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path

import psutil

logger = logging.getLogger(__name__)


class PeriodicOptimizer:
    """Runs periodic optimizations to prevent performance degradation"""

    def __init__(self, interval_minutes=15):
        self.interval_minutes = interval_minutes
        self.interval_seconds = interval_minutes * 60
        self.last_optimization = None
        self.optimization_count = 0

    def should_optimize(self):
        """Check if it's time to optimize"""
        if self.last_optimization is None:
            return True

        elapsed = time.time() - self.last_optimization
        return elapsed >= self.interval_seconds

    def get_memory_usage(self):
        """Get current memory usage in MB"""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024

    def clear_pycache(self, root_dir="."):
        """Clear all __pycache__ directories"""
        cleared = 0
        for pycache in Path(root_dir).rglob("__pycache__"):
            try:
                shutil.rmtree(pycache)
                cleared += 1
            except Exception as e:
                logger.warning(f"[!] Could not remove {pycache}: {e}")
        return cleared

    def clear_pyc_files(self, root_dir="."):
        """Clear all .pyc files"""
        cleared = 0
        for pyc in Path(root_dir).rglob("*.pyc"):
            try:
                pyc.unlink()
                cleared += 1
            except Exception as e:
                logger.warning(f"[!] Could not remove {pyc}: {e}")
        return cleared

    def clear_reflex_cache(self):
        """Clear Reflex-specific cache directories"""
        cleared = 0
        cache_dirs = [".web/.next", ".web/public", ".states"]

        for cache_dir in cache_dirs:
            cache_path = Path(cache_dir)
            if cache_path.exists() and cache_path.is_dir():
                # Only clear if it's large (>50MB)
                size_mb = (
                    sum(f.stat().st_size for f in cache_path.rglob("*") if f.is_file())
                    / 1024
                    / 1024
                )
                if size_mb > 50:
                    try:
                        # Don't delete the dir, just clear old files
                        for item in cache_path.rglob("*"):
                            if item.is_file():
                                # Clear files older than 1 hour
                                if time.time() - item.stat().st_mtime > 3600:
                                    item.unlink()
                                    cleared += 1
                    except Exception as e:
                        logger.warning(f"[!] Could not clear {cache_dir}: {e}")

        return cleared

    def optimize_memory(self):
        """Trigger garbage collection and memory cleanup"""
        import gc

        before = self.get_memory_usage()
        gc.collect()
        after = self.get_memory_usage()
        freed = before - after
        return freed

    def run_optimization(self):
        """Run periodic optimization tasks"""
        start_time = time.time()
        self.optimization_count += 1

        logger.info(
            f"\n[RESET] Running periodic optimization #{self.optimization_count}..."
        )
        logger.info(f"[-] Time: {datetime.now().strftime('%H:%M:%S')}")

        # 1. Check memory before
        mem_before = self.get_memory_usage()
        logger.info(f"[-] Memory before: {mem_before:.2f} MB")

        # 2. Clear Python caches
        pycache_cleared = self.clear_pycache()
        pyc_cleared = self.clear_pyc_files()
        if pycache_cleared or pyc_cleared:
            logger.info(
                f"[-] Cleared {pycache_cleared} __pycache__ dirs, {pyc_cleared} .pyc files"
            )

        # 3. Clear Reflex cache if needed
        reflex_cleared = self.clear_reflex_cache()
        if reflex_cleared:
            logger.info(f"[-] Cleared {reflex_cleared} old Reflex cache files")

        # 4. Optimize memory
        freed_mb = self.optimize_memory()
        logger.info(f"[-] Garbage collection freed: {freed_mb:.2f} MB")

        # 5. Check memory after
        mem_after = self.get_memory_usage()
        logger.info(f"[-] Memory after: {mem_after:.2f} MB")

        # 6. Calculate time taken
        elapsed = time.time() - start_time
        logger.info(f"[OK] Optimization complete in {elapsed:.2f}s")
        logger.info(f"[-] Next optimization in {self.interval_minutes} minutes\n")

        self.last_optimization = time.time()

        return {
            "timestamp": datetime.now().isoformat(),
            "memory_before_mb": mem_before,
            "memory_after_mb": mem_after,
            "memory_freed_mb": mem_before - mem_after,
            "pycache_cleared": pycache_cleared,
            "pyc_cleared": pyc_cleared,
            "reflex_cleared": reflex_cleared,
            "elapsed_seconds": elapsed,
        }

    def check_and_optimize(self):
        """Check if optimization is needed and run if so"""
        if self.should_optimize():
            return self.run_optimization()
        return None


# Global instance for use in application
periodic_optimizer = PeriodicOptimizer(interval_minutes=15)


def optimize_if_needed():
    """Quick check and optimize if needed - call this periodically in your app"""
    return periodic_optimizer.check_and_optimize()


if __name__ == "__main__":
    # Standalone mode - run optimization now
    optimizer = PeriodicOptimizer(interval_minutes=15)
    result = optimizer.run_optimization()
    print("\n[INFO] Optimization Result:")
    for key, value in result.items():
        print(f"  {key}: {value}")
