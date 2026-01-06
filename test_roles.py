import requests

BASE_URL = "http://127.0.0.1:8002"

def test_roles_api():
    # 1. Login as Admin
    resp = requests.post(f"{BASE_URL}/token", data={"username": "admin", "password": "admin123"})
    if resp.status_code != 200:
        print("Login failed:", resp.text)
        return
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Get Permissions
    resp = requests.get(f"{BASE_URL}/api/permissions", headers=headers)
    if resp.status_code != 200:
        print("Get Permissions failed:", resp.text)
        return
    perms = resp.json()
    print(f"Found {len(perms)} permissions.")
    
    # 3. Get Roles
    resp = requests.get(f"{BASE_URL}/api/roles", headers=headers)
    if resp.status_code != 200:
        print("Get Roles failed:", resp.text)
        return
    roles = resp.json()
    print(f"Found {len(roles)} roles.")
    
    # 4. Update Role Permissions (Test on Cashier)
    cashier_role = next((r for r in roles if r["name"] == "Cashier"), None)
    if not cashier_role:
        print("Cashier role not found")
        return
    
    print(f"Cashier currently has {len(cashier_role['permissions'])} permissions.")
    
    # Give Cashier ALL permissions temporarily
    all_perm_ids = [p["id"] for p in perms]
    resp = requests.put(f"{BASE_URL}/api/roles/{cashier_role['id']}/permissions", 
                        json={"permission_ids": all_perm_ids}, 
                        headers=headers)
    
    if resp.status_code == 200:
        print("Updated Cashier permissions successfully.")
    else:
        print("Update failed:", resp.text)

    # Verify
    resp = requests.get(f"{BASE_URL}/api/roles", headers=headers)
    roles = resp.json()
    cashier_role = next((r for r in roles if r["name"] == "Cashier"), None)
    print(f"Cashier now has {len(cashier_role['permissions'])} permissions.")

if __name__ == "__main__":
    try:
        test_roles_api()
    except Exception as e:
        print(f"Test failed (Server might not be running): {e}")
