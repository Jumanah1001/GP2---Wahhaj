"""
wahhaj/device.py
================
UML attributes:
    +deviceId         : UUID
    +model            : string
    +microcontroller  : string
    +storage          : string
    +battery          : string
    +altitudeSensor   : string
    +droneFrame       : string
"""

import uuid
from dataclasses import dataclass, field


@dataclass
class Device:
    """
    يمثّل طائرة مسيّرة واحدة بمواصفاتها الكاملة.

    Attributes (UML)
    ----------------
    deviceId        : UUID فريد
    model           : اسم الموديل (مثال: DJI Phantom 4 RTK)
    microcontroller : المعالج (مثال: STM32F4)
    storage         : سعة التخزين (مثال: 32GB)
    battery         : نوع البطارية أو سعتها (مثال: LiPo 5870mAh)
    altitudeSensor  : حساس الارتفاع (مثال: Barometer + GPS)
    droneFrame      : هيكل الطائرة (مثال: X500 V2)
    """

    model:           str = ""
    microcontroller: str = ""
    storage:         str = ""
    battery:         str = ""
    altitudeSensor:  str = ""
    droneFrame:      str = ""
    device_id:       str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def deviceId(self) -> str:
        return self.device_id

    @classmethod
    def create(
        cls,
        model:           str = "",
        microcontroller: str = "",
        storage:         str = "",
        battery:         str = "",
        altitudeSensor:  str = "",
        droneFrame:      str = "",
    ) -> "Device":
        return cls(
            model           = model,
            microcontroller = microcontroller,
            storage         = storage,
            battery         = battery,
            altitudeSensor  = altitudeSensor,
            droneFrame      = droneFrame,
        )

    def to_dict(self) -> dict:
        return {
            "deviceId":        self.device_id,
            "model":           self.model,
            "microcontroller": self.microcontroller,
            "storage":         self.storage,
            "battery":         self.battery,
            "altitudeSensor":  self.altitudeSensor,
            "droneFrame":      self.droneFrame,
        }

    def __repr__(self) -> str:
        return (f"Device(id={self.device_id[:8]}, model={self.model!r}, "
                f"frame={self.droneFrame!r})")
