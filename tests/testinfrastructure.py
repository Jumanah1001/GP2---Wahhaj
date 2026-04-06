# tests/test_infrastructure.py
import pytest
import numpy as np
import tempfile
import os

from wahhaj.models import Raster, Point, FileRef, BoundingBox, AOI, SiteInfo
from wahhaj.storage_service import StorageService
from wahhaj.device import Device
from wahhaj.User import User, UserRole, Session


# ── models ───────────────────────────────────────────────────────────────────

def test_raster_shape_and_nodata():
    r = Raster(data=np.random.rand(10, 10).astype(np.float32))
    assert r.shape == (10, 10) and r.nodata == -9999.0

def test_raster_statistics():
    r = Raster(data=np.array([[0.2, 0.8]], dtype=np.float32))
    s = r.statistics()
    assert s["count"] == 2 and abs(s["mean"] - 0.5) < 1e-5

def test_raster_statistics_ignores_nodata():
    r = Raster(data=np.array([[-9999.0, 0.6]], dtype=np.float32))
    assert r.statistics()["count"] == 1

def test_raster_transform_north_up():
    r = Raster(data=np.zeros((3, 3), dtype=np.float32))
    _, x_res, _, y_res = r.transform
    assert x_res > 0 and y_res < 0

def test_bounding_box_to_aoi():
    bb = BoundingBox(46.0, 24.0, 47.0, 25.0)
    aoi: AOI = bb.to_aoi()
    lon_min, lat_min, lon_max, lat_max = aoi
    assert lon_max > lon_min and lat_max > lat_min

def test_aoi_tuple_unpack():
    aoi: AOI = (46.0, 24.0, 47.0, 25.0)
    lon_min, lat_min, lon_max, lat_max = aoi
    assert lon_min == 46.0

def test_fileref_with_name():
    f = FileRef(path="/exports/map.pdf", size_bytes=1024, name="map.pdf")
    assert f.name == "map.pdf" and f.size_bytes == 1024

def test_siteinfo():
    si = SiteInfo(site_id="s1", description="zone", coordinates=(46.7, 24.5))
    assert si.coordinates[0] == 46.7


# ── StorageService ────────────────────────────────────────────────────────────

def test_storage_save_and_get():
    with tempfile.TemporaryDirectory() as tmp:
        s = StorageService(base_dir=tmp)
        assert s.save_file(b"hello", "img.png") is True
        ref = s.get("img.png")
        assert ref.size_bytes > 0 and ref.name == "img.png"

def test_storage_get_missing_raises():
    with tempfile.TemporaryDirectory() as tmp:
        s = StorageService(base_dir=tmp)
        with pytest.raises(FileNotFoundError):
            s.get("ghost.png")

def test_storage_put():
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "src.txt")
        open(src, "w").write("data")
        s   = StorageService(base_dir=tmp)
        ref = s.put(src)
        assert ref.size_bytes > 0 and ref.name == "src.txt"

def test_storage_nested_path():
    with tempfile.TemporaryDirectory() as tmp:
        s = StorageService(base_dir=tmp)
        assert s.save_file(b"x", "sub/file.bin") is True


# ── Device (UML) ──────────────────────────────────────────────────────────────

def test_device_all_uml_fields():
    d = Device.create(
        model           = "DJI Phantom 4 RTK",
        microcontroller = "STM32F4",
        storage         = "32GB",
        battery         = "LiPo 5870mAh",
        altitudeSensor  = "Barometer + GPS",
        droneFrame      = "X500 V2",
    )
    assert d.model           == "DJI Phantom 4 RTK"
    assert d.microcontroller == "STM32F4"
    assert d.storage         == "32GB"
    assert d.battery         == "LiPo 5870mAh"
    assert d.altitudeSensor  == "Barometer + GPS"
    assert d.droneFrame      == "X500 V2"
    assert d.deviceId is not None

def test_device_unique_ids():
    d1 = Device.create(model="DJI Mavic 3")
    d2 = Device.create(model="DJI Mavic 3")
    assert d1.deviceId != d2.deviceId

def test_device_to_dict():
    d = Device.create(model="DJI Mini 4 Pro", battery="LiPo 2590mAh")
    dd = d.to_dict()
    assert "deviceId" in dd and dd["battery"] == "LiPo 2590mAh"


# ── User (UML) ────────────────────────────────────────────────────────────────

def test_user_uml_attributes():
    u = User.create(name="Danah", email="danah@pnu.edu.sa", role=UserRole.ANALYST)
    assert u.userId    is not None
    assert u.name      == "Danah"
    assert u.role      == UserRole.ANALYST
    assert u.sessionId is not None
    assert u.createdAt is not None
    assert u.expiresAt is not None

def test_user_login_returns_session():
    u = User.create(name="Danah", email="danah@pnu.edu.sa")
    session = u.login("danah@pnu.edu.sa", "pw123")
    assert isinstance(session, Session)
    assert session.is_valid
    assert session.user_id == u.userId

def test_user_login_wrong_email_raises():
    u = User.create(name="X", email="x@x.com")
    with pytest.raises(ValueError):
        u.login("wrong@x.com", "pw")

def test_user_upload_data_files():
    from wahhaj.JobStatus import JobState
    u   = User.create(name="A", email="a@a.com", role=UserRole.ANALYST)
    job = u.uploadDataFiles(["file1.png", "file2.png"])
    assert job.state in (JobState.RUNNING, JobState.QUEUED, JobState.DONE)

def test_user_add_remove_user_admin():
    admin  = User.create(name="Admin", email="admin@pnu.edu.sa", role=UserRole.ADMIN)
    newbie = User.create(name="New",   email="new@pnu.edu.sa",   role=UserRole.ANALYST)
    admin.addUser(newbie)
    assert newbie.userId in User._user_registry
    admin.removeUser(newbie.userId)
    assert newbie.userId not in User._user_registry

def test_user_add_user_non_admin_raises():
    analyst = User.create(name="A", email="a@x.com", role=UserRole.ANALYST)
    other   = User.create(name="B", email="b@x.com")
    with pytest.raises(PermissionError):
        analyst.addUser(other)

def test_user_reset_password_admin():
    admin  = User.create(name="Admin", email="admin@x.com", role=UserRole.ADMIN)
    target = User.create(name="T",     email="t@x.com",     role=UserRole.ANALYST)
    target._hashed_password = "old_hash"
    admin.addUser(target)
    admin.resetPassword(target.userId)
    assert User._user_registry[target.userId]._hashed_password == ""
    admin.removeUser(target.userId)

def test_user_to_dict():
    u = User.create(name="Danah", email="danah@pnu.edu.sa")
    d = u.to_dict()
    for key in ("userId", "name", "role", "sessionId", "createdAt", "expiresAt"):
        assert key in d
