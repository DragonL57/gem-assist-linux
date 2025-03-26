"""
Location service for fetching and managing location information.
"""
import aiohttp
import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass
from functools import lru_cache # Removed

from ..settings import Settings, get_settings

@dataclass
class LocationInfo:
    """Location information container."""
    city: str
    country: str
    continent: str
    timezone: str
    currency_code: str
    currency_symbol: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    @property
    def formatted(self) -> str:
        """Get formatted location string."""
        return (
            f"Location: City: {self.city}, "
            f"Country: {self.country}, "
            f"Continent: {self.continent}, "
            f"Timezone: {self.timezone}, "
            f"Currency: {self.currency_symbol} ({self.currency_code})"
        )

class LocationServiceError(Exception):
    """Base exception for location service errors."""
    pass

class LocationFetchError(LocationServiceError):
    """Error fetching location data from API."""
    pass

class LocationParseError(LocationServiceError):
    """Error parsing location data."""
    pass

class LocationService:
    """Service for fetching and managing location information."""
    
    def __init__(self, location_api_url: str, location_timeout: int):
        """Initialize location service.

        Args:
            location_api_url: URL for location API
            location_timeout: Timeout for location API requests
        """
        self.location_api_url = location_api_url
        self.location_timeout = location_timeout
        self._location_cache: Optional[LocationInfo] = None
        
    async def get_location(self, force_refresh: bool = False) -> LocationInfo:
        """Get location information, optionally forcing a refresh.
        
        Args:
            force_refresh: Whether to force refresh cached data
            
        Returns:
            LocationInfo instance
            
        Raises:
            LocationFetchError: If location fetch fails
            LocationParseError: If location data parsing fails
        """
        if self._location_cache is not None and not force_refresh:
            return self._location_cache
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.location_api_url, # Use instance attributes
                    timeout=self.location_timeout # Use instance attributes
                ) as response:
                    if response.status != 200:
                        raise LocationFetchError(
                            f"Failed to fetch location data: HTTP {response.status}"
                        )
                    data = await response.json()
                    
            location = self._parse_location_data(data)
            self._location_cache = location
            return location

        except aiohttp.ClientError as e:
            raise LocationFetchError(f"Failed to fetch location data: {e}")
        except asyncio.TimeoutError:
            raise LocationFetchError("Location service request timed out")
        except Exception as e:
            raise LocationServiceError(f"Unexpected error in location service: {e}")

    def _parse_location_data(self, data: Dict[str, Any]) -> LocationInfo:
        """Parse raw location data into LocationInfo.
        
        Args:
            data: Raw location data from API
            
        Returns:
            LocationInfo instance
            
        Raises:
            LocationParseError: If required fields are missing
        """
        try:
            return LocationInfo(
                city=data.get("geoplugin_city", "Unknown"),
                country=data.get("geoplugin_countryName", "Unknown"),
                continent=data.get("geoplugin_continentName", "Unknown"),
                timezone=data.get("geoplugin_timezone", "Unknown"),
                currency_code=data.get("geoplugin_currencyCode", "Unknown"),
                currency_symbol=data.get("geoplugin_currencySymbol", "Unknown"),
                latitude=float(data["geoplugin_latitude"]) if "geoplugin_latitude" in data else None,
                longitude=float(data["geoplugin_longitude"]) if "geoplugin_longitude" in data else None
            )
        except (KeyError, ValueError, TypeError) as e:
            raise LocationParseError(f"Failed to parse location data: {e}")

def get_location_service(location_api_url: str, location_timeout: int) -> LocationService:
    """Get or create LocationService singleton.
    
    Args:
        location_api_url: URL for location API
        location_timeout: Timeout for location API requests
        
    Returns:
        LocationService instance
    """
    return LocationService(location_api_url, location_timeout)

# For backwards compatibility
async def get_location_info() -> str:
    """Get formatted location string (backwards compatibility).
    
    Returns:
        Formatted location string
    """
    try:
        service = get_location_service()
        location = await service.get_location()
        return location.formatted
    except LocationServiceError as e:
        return f"Location: Could not retrieve location information. Error: {e}"