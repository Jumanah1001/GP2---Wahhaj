

from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass
class Device:

    
    deviceId: UUID
    model: str
    microcontroller: str
    storage: str
    battery: str
    altitudeSensor: str
    droneFrame: str

    @staticmethod
    def create(
        model: str,
        microcontroller: str = "",
        storage: str = "",
        battery: str = "",
        altitudeSensor: str = "",
        droneFrame: str = ""
    ) -> "Device":
        """Create a new Device with auto-generated UUID."""
        return Device(
            deviceId=uuid4(),
            model=model,
            microcontroller=microcontroller,
            storage=storage,
            battery=battery,
            altitudeSensor=altitudeSensor,
            droneFrame=droneFrame
        )


# ============================================
# Tests
# ============================================

def test_device_creation():
    """Test creating a device using create() method."""
    drone = Device.create(
        model="DJI Phantom 4 RTK",
        microcontroller="ARM Cortex-M4",
        storage="16GB Internal",
        battery="LiPo 5870mAh",
        altitudeSensor="Barometer + GPS",
        droneFrame="Carbon Fiber Quadcopter"
    )
    
    assert drone.model == "DJI Phantom 4 RTK"
    assert drone.microcontroller == "ARM Cortex-M4"
    assert drone.storage == "16GB Internal"
    assert drone.battery == "LiPo 5870mAh"
    assert isinstance(drone.deviceId, UUID)
    print("Device creation test passed")


def test_device_with_defaults():
    """Test creating device with default empty values."""
    drone = Device.create(model="DJI Mavic 3")
    
    assert drone.model == "DJI Mavic 3"
    assert drone.microcontroller == ""
    assert drone.storage == ""
    assert drone.battery == ""
    assert isinstance(drone.deviceId, UUID)
    print("Device with defaults test passed")


def test_device_direct_construction():
    """Test creating device directly (not using create())."""
    device_id = uuid4()
    drone = Device(
        deviceId=device_id,
        model="Autel EVO II",
        microcontroller="Snapdragon",
        storage="8GB",
        battery="7100mAh",
        altitudeSensor="GPS+GLONASS",
        droneFrame="Foldable"
    )
    
    assert drone.deviceId == device_id
    assert drone.model == "Autel EVO II"
    assert drone.battery == "7100mAh"
    print(" Direct construction test passed")


def test_unique_device_ids():
    """Test that each created device has unique ID."""
    drone1 = Device.create(model="DJI Mini 3")
    drone2 = Device.create(model="DJI Mini 3")
    
    assert drone1.deviceId != drone2.deviceId
    print("Unique device IDs test passed")


if __name__ == "__main__":
    print("Running Device tests...\n")
    
    test_device_creation()
    test_device_with_defaults()
    test_device_direct_construction()
    test_unique_device_ids()
    
    print("\n" + "="*50)
    print("All tests passed! ")
    print("="*50)
    
    # Example usage
    print("\nExample usage:")
    print("-" * 50)
    
    d = Device.create(
        model="DJI Phantom 4 RTK",
        microcontroller="ARM Cortex-M4",
        storage="128GB",
        battery="5870mAh",
        altitudeSensor="Barometer",
        droneFrame="Quadcopter"
    )
    print(d)
