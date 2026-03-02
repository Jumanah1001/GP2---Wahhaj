
# ============================================================================
# DEMONSTRATION
# ============================================================================

def demo():
    """Demonstrate User class functionality"""
    
    print("="*80)
    print("USER CLASS DEMONSTRATION")
    print("="*80)
    print("\nNote: upload_data() requires JobStatus from teammate's module")
    print("="*80)
    
    # ========================================================================
    # 1. CREATE USERS
    # ========================================================================
    print("\n  CREATING USERS")
    print("-"*80)
    
    admin = User(
        name="Dr. Eman Aldakheel",
        email="eman.aldakheel@wahhaj.sa",
        role=UserRole.ADMIN,
        password="admin_secure_password"
    )
    print(f" Created: {admin}")
    
    analyst1 = User(
        name="Danah Alhamdi",
        email="danah@wahhaj.sa",
        role=UserRole.ANALYST,
        password="analyst_password_1"
    )
    print(f" Created: {analyst1}")
    
    analyst2 = User(
        name="Walah Alshwaier",
        email="walah@wahhaj.sa",
        role=UserRole.ANALYST,
        password="analyst_password_2"
    )
    print(f" Created: {analyst2}")
    
    # ========================================================================
    # 2. AUTHENTICATION
    # ========================================================================
    print("\n  AUTHENTICATION")
    print("-"*80)
    
    print("\n Admin Login:")
    session = admin.login("eman.aldakheel@wahhaj.sa", "admin_secure_password")
    print(f" Login successful!")
    print(f"  Session ID: {session.session_id}")
    print(f"  Expires at: {session.expires_at}")
    print(f"  {admin}")
    
    print("\n Analyst Login:")
    session = analyst1.login("danah@wahhaj.sa", "analyst_password_1")
    print(f" Login successful!")
    print(f"  {analyst1}")
    
    print("\n Failed Login Attempt:")
    try:
        analyst2.login("walah@wahhaj.sa", "wrong_password")
    except ValueError as e:
        print(f"✗ Login failed (as expected): {e}")
    
    # ========================================================================
    # 3. DATA UPLOAD (Placeholder - requires JobStatus)
    # ========================================================================
    print("\n  DATA UPLOAD (Requires JobStatus)")
    print("-"*80)
    
    files = [
        "/data/uav/flight_001_image_0001.tif",
        "/data/uav/flight_001_image_0002.tif",
        "/data/uav/flight_001_dem.tif"
    ]
    
    print("\n  Skipping upload_data() demo - requires JobStatus import")
    print(f"   Files ready: {len(files)} files")
    # analyst1.upload_data(files)  # Uncomment when JobStatus is available
    
    # ========================================================================
    # 4. ADMIN OPERATIONS
    # ========================================================================
    print("\n  ADMIN OPERATIONS")
    print("-"*80)
    
    print("\n Listing all users (Admin operation):")
    all_users = admin.list_all_users()
    for i, user in enumerate(all_users, 1):
        print(f"  {i}. {user.name} ({user.email}) - {user.role.value}")
    
    print("\n Adding new user (Admin operation):")
    new_analyst = User(
        name="Ruba Aletri",
        email="ruba@wahhaj.sa",
        role=UserRole.ANALYST,
        password="new_analyst_password"
    )
    admin.add_user(new_analyst)
    
    print("\n Resetting user password (Admin operation):")
    new_pwd = admin.reset_password(analyst2.user_id)
    print(f"  New password for {analyst2.name}: {new_pwd}")
    
    print("\n Attempting admin operation as Analyst (should fail):")
    try:
        analyst1.list_all_users()
    except PermissionError as e:
        print(f" Operation denied (as expected): {e}")
    
    print("\n Removing user (Admin operation):")
    admin.remove_user(new_analyst.user_id)
    
    # ========================================================================
    # 5. SESSION MANAGEMENT
    # ========================================================================
    print("\n  SESSION MANAGEMENT")
    print("-"*80)
    
    print(f"\n Current session valid: {admin.is_authenticated()}")
    print(f"   Expires at: {admin.expires_at}")
    
    print("\n Refreshing session:")
    refreshed = admin.refresh_session()
    print(f" Session refreshed")
    print(f"  New expiration: {refreshed.expires_at}")
    
    print("\n Logging out:")
    admin.logout()
    print(f" Logged out")
    print(f"  Authenticated: {admin.is_authenticated()}")
    
    # ========================================================================
    # 6. PASSWORD CHANGE
    # ========================================================================
    print("\n  PASSWORD CHANGE")
    print("-"*80)
    
    print("\n User changing own password:")
    analyst1.change_password("analyst_password_1", "new_secure_password_123")
    
    print("\n Verifying new password works:")
    session = analyst1.login("danah@wahhaj.sa", "new_secure_password_123")
    print(f" Login successful with new password!")
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "="*80)
    print("DEMONSTRATION COMPLETE")
    print("="*80)
    print(f"\nTotal users in system: {len(User._users_db)}")
    print(f"Active sessions: {len(User._sessions_db)}")
    print("\n All functionality demonstrated successfully!")
    print("\n To enable upload_data():")
    print("   Add: from jobstatus_module import JobStatus")


if __name__ == "__main__":
    demo()
