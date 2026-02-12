class ExternalDataSourceAdapter:
     #Adapter class is for fetching external environmental data
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        
    def fetch_ghi(self, aoi: tuple, time: datetime) -> Raster:
        """Fetch Global Horizontal Irradiance data
        
        Args:
            aoi: Area of interest (xmin, ymin, xmax, ymax)
            time: Time period for data
            
        Returns:
            Raster with GHI values (kWh/m²/day)
        """
        # TODO: Integrate with APIs like:
        # - NASA POWER
        # - Solargis
        # - PVGIS
        pass
    
    def fetch_lst(self, aoi: tuple, time: datetime) -> Raster:
        """Fetch Land Surface Temperature data
        
        Args:
            aoi: Area of interest
            time: Time period
            
        Returns:
            Raster with LST values (°C)
        """
        # TODO: Integrate with satellite data sources:
        # - Landsat
        # - MODIS
        # - Sentinel
        pass
    
    def fetch_sunshine_hours(self, aoi: tuple, time: datetime) -> Raster:
        """Fetch sunshine hours data
        
        Returns:
            Raster with sunshine hours per day
        """
        # TODO: Fetch from meteorological data sources
        pass
    
    def fetch_elevation(self, aoi: tuple, time: datetime) -> Raster:
        """Fetch elevation/DEM data
        
        Returns:
            Raster with elevation values (meters)
        """
        # TODO: Fetch DEM from sources like:
        # - SRTM
        # - ASTER GDEM
        # - Local Saudi Arabia elevation data
        pass
