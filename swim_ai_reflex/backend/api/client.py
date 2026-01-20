"""
API Client for AquaForge

This module provides a Python client for interacting with the AquaForge FastAPI backend.
It can be used by:
- The Reflex frontend (if migrating away from state-based calls)
- External applications
- CLI tools
- Test automation

Usage:
    from swim_ai_reflex.backend.api.client import AquaForgeClient
    
    client = AquaForgeClient("http://localhost:8001")
    result = await client.optimize(seton_data, opponent_data)
"""

import httpx
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Result from an optimization request."""
    success: bool
    seton_score: float
    opponent_score: float
    margin: float
    results: List[Dict[str, Any]]
    warnings: List[str]
    time_ms: float


@dataclass  
class TeamDataResult:
    """Result from a team data upload."""
    success: bool
    team_name: str
    swimmer_count: int
    entry_count: int
    events: List[str]
    warnings: List[str]


class AquaForgeClient:
    """
    Async client for the AquaForge API.
    
    Example:
        async with AquaForgeClient("http://localhost:8001") as client:
            health = await client.health_check()
            print(health)
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8001",
        timeout: float = 60.0,
        api_key: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def connect(self):
        """Initialize the HTTP client."""
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=headers,
        )
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _ensure_connected(self):
        if not self._client:
            raise RuntimeError("Client not connected. Use 'async with' or call connect()")
    
    # ==================== Health ====================
    
    async def health_check(self) -> Dict[str, Any]:
        """Check API health status."""
        self._ensure_connected()
        response = await self._client.get("/health")
        response.raise_for_status()
        return response.json()
    
    async def is_ready(self) -> bool:
        """Check if API is ready."""
        self._ensure_connected()
        try:
            response = await self._client.get("/ready")
            return response.status_code == 200
        except Exception:
            return False
    
    # ==================== Optimization ====================
    
    async def optimize(
        self,
        seton_data: List[Dict[str, Any]],
        opponent_data: List[Dict[str, Any]],
        optimizer_backend: str = "heuristic",
        max_individual_events: int = 4,
        enforce_fatigue: bool = True,
    ) -> OptimizationResult:
        """
        Run lineup optimization.
        
        Args:
            seton_data: Seton team entries
            opponent_data: Opponent team entries
            optimizer_backend: 'heuristic' or 'gurobi'
            max_individual_events: Max events per swimmer
            enforce_fatigue: Apply fatigue modeling
            
        Returns:
            OptimizationResult with scores and lineup
        """
        self._ensure_connected()
        
        response = await self._client.post(
            "/api/v1/optimize",
            json={
                "seton_data": seton_data,
                "opponent_data": opponent_data,
                "optimizer_backend": optimizer_backend,
                "max_individual_events": max_individual_events,
                "enforce_fatigue": enforce_fatigue,
            }
        )
        response.raise_for_status()
        data = response.json()
        
        return OptimizationResult(
            success=data.get("success", False),
            seton_score=data.get("seton_score", 0),
            opponent_score=data.get("opponent_score", 0),
            margin=data.get("score_margin", 0),
            results=data.get("results", []),
            warnings=data.get("warnings", []),
            time_ms=data.get("optimization_time_ms", 0),
        )
    
    async def preview_optimization(
        self,
        seton_data: List[Dict[str, Any]],
        opponent_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Get a preview of optimization without running it."""
        self._ensure_connected()
        
        response = await self._client.post(
            "/api/v1/optimize/preview",
            json={
                "seton_data": seton_data,
                "opponent_data": opponent_data,
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def list_backends(self) -> Dict[str, Any]:
        """List available optimization backends."""
        self._ensure_connected()
        response = await self._client.get("/api/v1/optimize/backends")
        response.raise_for_status()
        return response.json()
    
    # ==================== Data ====================
    
    async def upload_team_file(
        self,
        file_path: str,
        team_type: str,
        team_name: Optional[str] = None,
    ) -> TeamDataResult:
        """
        Upload a team roster file.
        
        Args:
            file_path: Path to the Excel/CSV file
            team_type: 'seton' or 'opponent'
            team_name: Optional team name override
        """
        self._ensure_connected()
        
        with open(file_path, "rb") as f:
            files = {"file": f}
            data = {"team_type": team_type}
            if team_name:
                data["team_name"] = team_name
            
            response = await self._client.post(
                "/api/v1/data/upload",
                files=files,
                data=data,
            )
        
        response.raise_for_status()
        result = response.json()
        
        return TeamDataResult(
            success=result.get("success", False),
            team_name=result.get("team_name", ""),
            swimmer_count=result.get("swimmer_count", 0),
            entry_count=result.get("entry_count", 0),
            events=result.get("unique_events", []),
            warnings=result.get("warnings", []),
        )
    
    async def submit_team_data(
        self,
        team_name: str,
        team_type: str,
        entries: List[Dict[str, Any]],
    ) -> TeamDataResult:
        """Submit team data directly as JSON."""
        self._ensure_connected()
        
        response = await self._client.post(
            "/api/v1/data/team",
            json={
                "team_name": team_name,
                "team_type": team_type,
                "entries": entries,
            }
        )
        response.raise_for_status()
        result = response.json()
        
        return TeamDataResult(
            success=result.get("success", False),
            team_name=result.get("team_name", ""),
            swimmer_count=result.get("swimmer_count", 0),
            entry_count=result.get("entry_count", 0),
            events=result.get("unique_events", []),
            warnings=result.get("warnings", []),
        )
    
    async def get_events(self) -> List[Dict[str, Any]]:
        """Get list of standard swim events."""
        self._ensure_connected()
        response = await self._client.get("/api/v1/data/events")
        response.raise_for_status()
        return response.json().get("events", [])
    
    # ==================== Export ====================
    
    async def export_results(
        self,
        optimization_results: Dict[str, Any],
        format: str = "csv",
        seton_score: float = 0,
        opponent_score: float = 0,
    ) -> Dict[str, Any]:
        """
        Export optimization results.
        
        Args:
            optimization_results: Results from optimization
            format: 'csv', 'json', 'html', or 'pdf'
            
        Returns:
            Export response with content or download URL
        """
        self._ensure_connected()
        
        response = await self._client.post(
            "/api/v1/export",
            json={
                "format": format,
                "optimization_results": optimization_results,
                "seton_score": seton_score,
                "opponent_score": opponent_score,
            }
        )
        response.raise_for_status()
        return response.json()
    
    # ==================== Analytics ====================
    
    async def compare_teams(
        self,
        seton_data: List[Dict[str, Any]],
        opponent_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Compare two teams."""
        self._ensure_connected()
        
        response = await self._client.post(
            "/api/v1/analytics/compare",
            json={
                "seton_data": seton_data,
                "opponent_data": opponent_data,
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def analyze_depth(
        self,
        team_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Analyze team depth."""
        self._ensure_connected()
        
        response = await self._client.post(
            "/api/v1/analytics/depth",
            json=team_data,
        )
        response.raise_for_status()
        return response.json()
    
    async def get_scoring_rules(self) -> Dict[str, Any]:
        """Get scoring rules."""
        self._ensure_connected()
        response = await self._client.get("/api/v1/analytics/scoring")
        response.raise_for_status()
        return response.json()


# Synchronous wrapper for non-async contexts
class AquaForgeClientSync:
    """Synchronous wrapper for AquaForgeClient."""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self._async_client = AquaForgeClient(base_url)
    
    def _run(self, coro):
        """Run async coroutine synchronously."""
        return asyncio.get_event_loop().run_until_complete(coro)
    
    def health_check(self) -> Dict[str, Any]:
        async def _do():
            async with AquaForgeClient(self._async_client.base_url) as client:
                return await client.health_check()
        return self._run(_do())
    
    def optimize(self, seton_data, opponent_data, **kwargs) -> OptimizationResult:
        async def _do():
            async with AquaForgeClient(self._async_client.base_url) as client:
                return await client.optimize(seton_data, opponent_data, **kwargs)
        return self._run(_do())


# Quick test function
async def _test_client():
    """Test the client against a running API."""
    async with AquaForgeClient() as client:
        print("Testing health check...")
        health = await client.health_check()
        print(f"  Status: {health['status']}")
        
        print("Testing events list...")
        events = await client.get_events()
        print(f"  Found {len(events)} events")
        
        print("Testing scoring rules...")
        rules = await client.get_scoring_rules()
        print(f"  1st place individual: {rules['individual_events']['1st']} points")
        
        print("✅ All client tests passed!")


if __name__ == "__main__":
    asyncio.run(_test_client())
