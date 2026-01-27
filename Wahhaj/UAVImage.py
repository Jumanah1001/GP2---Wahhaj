from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional, Dict



class UAVImage: #Represents a single UAV image
    
    def __init__(self, filePath: str , resolution: str, timestamp: Optional[datetime]= None,imageId: Optional[UUID] = None, ):
        self.imageId = imageId or uuid4()
        self.filePath = filePath
        self.resolution = resolution
        self.timestamp = timestamp or datetime.utcnow()
        #end of constructor


    def  extractMetadata(self) -> Dict[str,str]:
        # implementation for extracting metadata from the image
        metadata = {"filePath": self.filePath, "resolution": self.resolution, "timestamp": self.timestamp.isoformat()}
        return metadata

    def geoReference(self) -> None:
        """
        Applies georeferencing to the image.
        Actual GIS logic will be implemented later.
        """
        # Placeholder for georeferencing logic
        # Example: attach CRS, ground control points, etc.
        pass



 #------------------- test------------------   
img = UAVImage("data/image.tif", "4096x2160")
print(img.extractMetadata())

""" output:
{'filePath': 'data/image.tif', 'resolution': '4096x2160', 'timestamp': '2026-01-27T10:10:20.116981'}
"""

