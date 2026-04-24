# ============================================================
# test_person_a.py
# تيستات شخص A — User + Device + StorageService + models
# تشغيل: pytest test_person_a.py -v
# ============================================================

import pytest
import numpy as np
import os

try:
    from .models import Raster, Point, FileRef, BoundingBox, SiteInfo
except ImportError:
    from Wahhaj.models import Raster, Point, FileRef, BoundingBox, SiteInfo

try:
    from .storage_service import StorageService
    from .User import User, UserRole, Session
    from .device import Device
except ImportError:
    from Wahhaj.storage_service import StorageService
    from Wahhaj.User import User, UserRole, Session
    from Wahhaj.device import Device


# ============================================================
# SECTION 1 — models.py
# ============================================================

class TestRaster:

    def test_creation_basic(self):
        r = Raster(data=np.zeros((5, 5), dtype=np.float32))
        assert r.data is not None
        assert r.nodata == -9999.0
        assert r.crs == "EPSG:4326"

    def test_shape(self):
        r = Raster(data=np.zeros((5, 5), dtype=np.float32))
        assert r.shape == (5, 5)

    def test_statistics_normal(self):
        data = np.array([[0.0, 0.5], [0.75, 1.0]], dtype=np.float32)
        stats = Raster(data=data).statistics()
        assert stats["count"] == 4
        assert abs(stats["min"]  - 0.0)    < 0.001
        assert abs(stats["max"]  - 1.0)    < 0.001
        assert abs(stats["mean"] - 0.5625) < 0.001

    def test_statistics_ignores_nodata(self):
        data = np.array([[0.5, -9999.0], [1.0, -9999.0]], dtype=np.float32)
        stats = Raster(data=data).statistics()
        assert stats["count"] == 2
        assert abs(stats["mean"] - 0.75) < 0.001

    def test_statistics_all_nodata(self):
        data = np.full((3, 3), -9999.0, dtype=np.float32)
        stats = Raster(data=data).statistics()
        assert stats["count"] == 0
        assert stats["mean"] is None

    def test_metadata_stored(self):
        r = Raster(data=np.zeros((5, 5), dtype=np.float32),
                   metadata={"layer": "ghi", "source": "open-meteo"})
        assert r.metadata["layer"]  == "ghi"
        assert r.metadata["source"] == "open-meteo"

    def test_5x5_grid(self):
        data = np.random.rand(5, 5).astype(np.float32)
        r = Raster(data=data)
        assert r.shape == (5, 5)
        stats = r.statistics()
        assert stats["min"] <= stats["max"]


class TestPoint:

    def test_creation(self):
        p = Point(lon=46.7, lat=24.7)
        assert p.lon == 46.7 and p.lat == 24.7

    def test_str_contains_coords(self):
        p = Point(lon=46.7, lat=24.7)
        assert "24.7" in str(p) and "46.7" in str(p)

    def test_negative_coords(self):
        p = Point(lon=-120.0, lat=-35.0)
        assert p.lon == -120.0 and p.lat == -35.0

    def test_riyadh_coords(self):
        p = Point(lon=46.6753, lat=24.6877)
        assert 46.0 < p.lon < 47.0
        assert 24.0 < p.lat < 25.0


class TestFileRef:

    def test_creation(self):
        f = FileRef(path="/tmp/test.pdf", name="test.pdf", size_bytes=1024)
        assert f.path == "/tmp/test.pdf"
        assert f.name == "test.pdf"
        assert f.size_bytes == 1024

    def test_defaults(self):
        f = FileRef(path="/tmp/file.pdf")
        assert f.size_bytes == 0
        assert f.name == ""


class TestBoundingBox:

    def test_creation(self):
        bb = BoundingBox(xmin=46.0, ymin=24.0, xmax=47.0, ymax=25.0)
        assert bb.xmin == 46.0 and bb.ymax == 25.0

    def test_to_tuple(self):
        bb = BoundingBox(xmin=46.0, ymin=24.0, xmax=47.0, ymax=25.0)
        assert bb.to_tuple() == (46.0, 24.0, 47.0, 25.0)

    def test_to_aoi(self):
        aoi = BoundingBox(xmin=46.0, ymin=24.0, xmax=47.0, ymax=25.0).to_aoi()
        assert len(aoi) == 4
        assert aoi[0] == 46.0


class TestSiteInfo:

    def test_creation(self):
        si = SiteInfo(site_id="s1",
                      description="Tabuk — high suitability",
                      coordinates=(36.8, 28.5))
        assert si.site_id == "s1"
        assert "Tabuk" in si.description
        assert si.coordinates == (36.8, 28.5)

    def test_coordinates_format(self):
        lon, lat = SiteInfo(site_id="s2", description="x",
                            coordinates=(36.8, 28.5)).coordinates
        assert 36.0 < lon < 37.0
        assert 28.0 < lat < 29.0


# ============================================================
# SECTION 2 — storage_service.py
# ============================================================

class TestStorageService:

    @pytest.fixture
    def storage(self, tmp_path):
        return StorageService(base_dir=str(tmp_path / "storage"))

    @pytest.fixture
    def sample_file(self, tmp_path):
        f = tmp_path / "image.png"
        f.write_bytes(b"\x89PNG\r\n" + b"\x00" * 100)
        return str(f)

    # save_file
    def test_save_returns_true(self, storage):
        assert storage.save_file(b"data", "test.txt") is True

    def test_save_content_correct(self, storage):
        storage.save_file(b"WAHHAJ", "f.txt")
        with open(storage.get("f.txt").path, "rb") as f:
            assert f.read() == b"WAHHAJ"

    def test_save_size_correct(self, storage):
        storage.save_file(b"X" * 200, "big.txt")
        assert storage.get("big.txt").size_bytes == 200

    def test_save_creates_subdirs(self, storage):
        assert storage.save_file(b"d", "a/b/c.txt") is True

    def test_save_multiple_files(self, storage):
        for i in range(5):
            storage.save_file(f"file{i}".encode(), f"f{i}.txt")
        for i in range(5):
            assert storage.get(f"f{i}.txt") is not None

    # get
    def test_get_returns_fileref(self, storage):
        storage.save_file(b"hi", "hello.txt")
        ref = storage.get("hello.txt")
        assert isinstance(ref, FileRef)
        assert ref.size_bytes > 0

    def test_get_nonexistent_raises(self, storage):
        with pytest.raises(FileNotFoundError):
            storage.get("ghost.txt")

    # put
    def test_put_file(self, storage, sample_file):
        ref = storage.put(sample_file)
        assert isinstance(ref, FileRef)
        assert os.path.exists(ref.path)

    # delete
    def test_delete_existing(self, storage):
        storage.save_file(b"bye", "del.txt")
        assert storage.delete_file("del.txt") is True

    def test_delete_nonexistent_returns_false(self, storage):
        assert storage.delete_file("none.txt") is False

    def test_file_gone_after_delete(self, storage):
        storage.save_file(b"x", "gone.txt")
        storage.delete_file("gone.txt")
        with pytest.raises(FileNotFoundError):
            storage.get("gone.txt")

    def test_upload_service_contract(self, storage):
        """UploadService._file_exists يعتمد على get() ترفع FileNotFoundError"""
        exists = True
        try:
            storage.get("no.jpg")
        except FileNotFoundError:
            exists = False
        assert exists is False

    def test_full_lifecycle(self, storage):
        assert storage.save_file(b"life", "lc.txt") is True
        ref = storage.get("lc.txt")
        assert ref.size_bytes == 4
        assert storage.delete_file("lc.txt") is True
        with pytest.raises(FileNotFoundError):
            storage.get("lc.txt")


# ============================================================
# SECTION 3 — User.py
# ============================================================

class TestUser:

    @pytest.fixture(autouse=True)
    def clear_registry(self):
        """تنظيف الـ registry قبل كل تيست"""
        User._user_registry.clear()
        yield
        User._user_registry.clear()

    @pytest.fixture
    def admin(self):
        return User(name="Dr. Eman", email="eman@wahhaj.sa",
                    role=UserRole.ADMIN, hashed_password="admin123")

    @pytest.fixture
    def analyst(self):
        return User(name="Danah Alhamdi", email="danah@wahhaj.sa",
                    role=UserRole.ANALYST, hashed_password="pass123")

    # إنشاء
    def test_creation_basic(self, analyst):
        assert analyst.name  == "Danah Alhamdi"
        assert analyst.role  == UserRole.ANALYST
        assert analyst.userId is not None

    def test_unique_ids(self):
        u1 = User(name="A", email="a@w.sa")
        u2 = User(name="B", email="b@w.sa")
        assert u1.userId != u2.userId

    def test_create_classmethod(self):
        u = User.create(name="Walah", email="walah@w.sa",
                        role=UserRole.ANALYST)
        assert u.name == "Walah"
        assert u.role == UserRole.ANALYST

    def test_default_role_analyst(self):
        u = User(name="X", email="x@w.sa")
        assert u.role == UserRole.ANALYST

    # login
    def test_login_success(self, analyst):
        session = analyst.login("danah@wahhaj.sa", "anypassword")
        assert session is not None
        assert session.user_id == analyst.userId

    def test_login_wrong_email_raises(self, analyst):
        with pytest.raises(ValueError):
            analyst.login("wrong@email.com", "pass")

    def test_login_returns_session(self, analyst):
        session = analyst.login("danah@wahhaj.sa", "pass")
        assert isinstance(session, Session)
        assert session.session_id is not None

    def test_login_updates_session_id(self, analyst):
        session = analyst.login("danah@wahhaj.sa", "pass")
        assert analyst.sessionId == session.session_id

    # addUser — Admin only
    def test_add_user_by_admin(self, admin, analyst):
        admin.addUser(analyst)
        assert analyst.userId in User._user_registry

    def test_add_user_by_analyst_raises(self, analyst):
        other = User(name="X", email="x@w.sa")
        with pytest.raises(PermissionError):
            analyst.addUser(other)

    # removeUser — Admin only
    def test_remove_user_by_admin(self, admin, analyst):
        admin.addUser(analyst)
        admin.removeUser(analyst.userId)
        assert analyst.userId not in User._user_registry

    def test_remove_user_by_analyst_raises(self, analyst):
        with pytest.raises(PermissionError):
            analyst.removeUser("some-id")

    def test_remove_nonexistent_no_error(self, admin):
        admin.removeUser("non-existent-id")  # لا يرفع exception

    # resetPassword — Admin only
    def test_reset_password_by_admin(self, admin, analyst):
        admin.addUser(analyst)
        admin.resetPassword(analyst.userId)
        assert User._user_registry[analyst.userId]._hashed_password == ""

    def test_reset_password_by_analyst_raises(self, analyst):
        with pytest.raises(PermissionError):
            analyst.resetPassword("some-id")

    # to_dict
    def test_to_dict_keys(self, analyst):
        d = analyst.to_dict()
        for key in ["userId", "name", "email", "role", "sessionId"]:
            assert key in d

    def test_to_dict_role_is_string(self, analyst):
        assert isinstance(analyst.to_dict()["role"], str)

    def test_repr(self, analyst):
        r = repr(analyst)
        assert "Danah" in r
        assert "Analyst" in r

    # uploadDataFiles
    def test_upload_files_active_user(self, analyst):
        job = analyst.uploadDataFiles(["img1.jpg", "img2.jpg"])
        assert job is not None

    def test_upload_files_inactive_user(self):
        u = User(name="Inactive", email="i@w.sa", is_active=False)
        job = u.uploadDataFiles(["img.jpg"])
        assert job is not None  # يرجع job بـ error state


# ============================================================
# SECTION 4 — device.py
# ============================================================

class TestDevice:

    @pytest.fixture
    def drone(self):
        return Device(
            model="DJI Phantom 4 RTK",
            microcontroller="STM32F4",
            storage="32GB",
            battery="LiPo 5870mAh",
            altitudeSensor="Barometer + GPS",
            droneFrame="X500 V2",
        )

    # إنشاء
    def test_creation_full(self, drone):
        assert drone.model           == "DJI Phantom 4 RTK"
        assert drone.microcontroller == "STM32F4"
        assert drone.storage         == "32GB"
        assert drone.battery         == "LiPo 5870mAh"
        assert drone.altitudeSensor  == "Barometer + GPS"
        assert drone.droneFrame      == "X500 V2"

    def test_device_id_generated(self, drone):
        assert drone.deviceId is not None
        assert len(drone.deviceId) > 0

    def test_unique_device_ids(self):
        d1 = Device(model="A")
        d2 = Device(model="B")
        assert d1.deviceId != d2.deviceId

    def test_default_empty_strings(self):
        d = Device()
        assert d.model           == ""
        assert d.microcontroller == ""
        assert d.storage         == ""

    def test_device_id_property(self, drone):
        assert drone.deviceId == drone.device_id

    # create classmethod
    def test_create_classmethod(self):
        d = Device.create(model="DJI Mavic 3", storage="64GB",
                          battery="5000mAh")
        assert d.model   == "DJI Mavic 3"
        assert d.storage == "64GB"

    def test_create_partial_fields(self):
        d = Device.create(model="TestDrone")
        assert d.model   == "TestDrone"
        assert d.storage == ""

    # to_dict
    def test_to_dict_has_all_keys(self, drone):
        d = drone.to_dict()
        for key in ["deviceId", "model", "microcontroller",
                    "storage", "battery", "altitudeSensor", "droneFrame"]:
            assert key in d

    def test_to_dict_values_correct(self, drone):
        d = drone.to_dict()
        assert d["model"]   == "DJI Phantom 4 RTK"
        assert d["storage"] == "32GB"

    def test_to_dict_id_matches(self, drone):
        assert drone.to_dict()["deviceId"] == drone.deviceId

    def test_repr(self, drone):
        assert "DJI Phantom 4 RTK" in repr(drone)

    def test_multiple_devices_independent(self):
        d1 = Device.create(model="Drone A", storage="16GB")
        d2 = Device.create(model="Drone B", storage="64GB")
        assert d1.model    != d2.model
        assert d1.deviceId != d2.deviceId


# ============================================================
# SECTION 5 — Integration
# ============================================================

class TestIntegration:

    def test_raster_save_and_reload(self, tmp_path):
        """Raster يُحفظ ويُقرأ عبر StorageService بدون فقدان بيانات"""
        storage = StorageService(base_dir=str(tmp_path))
        data    = np.random.rand(5, 5).astype(np.float32)
        r       = Raster(data=data, metadata={"layer": "ghi"})
        raw     = r.data.tobytes()

        storage.save_file(raw, "ghi.bin")
        ref = storage.get("ghi.bin")
        assert ref.size_bytes == len(raw)

        with open(ref.path, "rb") as f:
            loaded = np.frombuffer(f.read(), dtype=np.float32).reshape(5, 5)
        np.testing.assert_array_almost_equal(r.data, loaded)

    def test_user_storage_together(self, tmp_path):
        """User يرفع ملف → StorageService يحفظه → FileRef صحيح"""
        storage = StorageService(base_dir=str(tmp_path))
        User._user_registry.clear()
        user    = User(name="Danah", email="danah@w.sa")

        storage.save_file(b"\x89PNG" + b"\x00" * 50, "drone.png")
        ref = storage.get("drone.png")
        assert isinstance(ref, FileRef)
        assert ref.size_bytes > 0

    def test_admin_manages_users_and_device(self):
        """Admin يضيف user + ينشئ Device — لا تعارض"""
        User._user_registry.clear()
        admin   = User(name="Admin",   email="admin@w.sa", role=UserRole.ADMIN)
        analyst = User(name="Analyst", email="analyst@w.sa")
        drone   = Device.create(model="DJI RTK", storage="32GB")

        admin.addUser(analyst)
        assert analyst.userId in User._user_registry
        assert drone.model == "DJI RTK"
        User._user_registry.clear()
