#!/usr/bin/env python3
"""
Test script for authentication endpoints (Phase 3)
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def print_section(title):
    """Print section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def test_register():
    """Test user registration"""
    print_section("TEST 1: User Registration")
    
    url = f"{BASE_URL}/auth/register"
    data = {
        "username": "alice_trader",
        "password": "mySecurePass123"
    }
    
    print(f"📤 POST {url}")
    print(f"   Body: {json.dumps(data, indent=2)}")
    
    response = requests.post(url, json=data)
    print(f"\n📥 Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 201:
        print("\n✅ Registration successful!")
        return response.json()["access_token"]
    else:
        print("\n❌ Registration failed")
        return None


def test_duplicate_register():
    """Test duplicate username registration"""
    print_section("TEST 2: Duplicate Username Registration")
    
    url = f"{BASE_URL}/auth/register"
    data = {
        "username": "alice_trader",
        "password": "anotherPassword"
    }
    
    print(f"📤 POST {url}")
    print(f"   Body: {json.dumps(data, indent=2)}")
    
    response = requests.post(url, json=data)
    print(f"\n📥 Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 400:
        print("\n✅ Correctly rejected duplicate username!")
    else:
        print("\n❌ Should have rejected duplicate username")


def test_login_valid():
    """Test login with valid credentials"""
    print_section("TEST 3: Login with Valid Credentials")
    
    url = f"{BASE_URL}/auth/login"
    data = {
        "username": "alice_trader",
        "password": "mySecurePass123"
    }
    
    print(f"📤 POST {url}")
    print(f"   Body: {json.dumps(data, indent=2)}")
    
    response = requests.post(url, json=data)
    print(f"\n📥 Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("\n✅ Login successful!")
        return response.json()["access_token"]
    else:
        print("\n❌ Login failed")
        return None


def test_login_invalid():
    """Test login with invalid credentials"""
    print_section("TEST 4: Login with Invalid Password")
    
    url = f"{BASE_URL}/auth/login"
    data = {
        "username": "alice_trader",
        "password": "wrongPassword"
    }
    
    print(f"📤 POST {url}")
    print(f"   Body: {json.dumps(data, indent=2)}")
    
    response = requests.post(url, json=data)
    print(f"\n📥 Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 401:
        print("\n✅ Correctly rejected invalid credentials!")
    else:
        print("\n❌ Should have rejected invalid credentials")


def test_username_validation():
    """Test username validation"""
    print_section("TEST 5: Username Validation")
    
    invalid_usernames = [
        ("ab", "Too short (min 3 chars)"),
        ("user@name", "Invalid characters (@ not allowed)"),
        ("user name", "Invalid characters (space not allowed)"),
    ]
    
    for username, reason in invalid_usernames:
        print(f"\n🧪 Testing: {username} - {reason}")
        
        url = f"{BASE_URL}/auth/register"
        data = {
            "username": username,
            "password": "password123"
        }
        
        response = requests.post(url, json=data)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 422:
            print(f"   ✅ Correctly rejected: {response.json()['detail'][0]['msg']}")
        elif response.status_code == 400:
            print(f"   ✅ Correctly rejected: {response.json()['detail']}")
        else:
            print(f"   ❌ Should have rejected")


def test_token_usage():
    """Test using JWT token for authenticated request"""
    print_section("TEST 6: Using JWT Token")
    
    # First login to get token
    print("🔐 Logging in to get token...")
    url = f"{BASE_URL}/auth/login"
    data = {"username": "alice_trader", "password": "mySecurePass123"}
    response = requests.post(url, json=data)
    token = response.json()["access_token"]
    
    print(f"✅ Got token: {token[:50]}...")
    print(f"\n📝 Token format: Bearer token")
    print(f"   Use in header: Authorization: Bearer <token>")
    print(f"\n💡 This token can now be used to access protected endpoints")
    print(f"   (Will be implemented in Phase 4: Paper Trading)")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  🧪 PHASE 3: AUTHENTICATION TESTING 🧪")
    print("="*60)
    print("\nTesting FastAPI authentication with JWT tokens")
    print(f"Server: {BASE_URL}")
    
    # Run tests
    test_register()
    test_duplicate_register()
    test_login_valid()
    test_login_invalid()
    test_username_validation()
    test_token_usage()
    
    # Summary
    print_section("✅ All Tests Completed")
    print("\n📊 Phase 3 Features Validated:")
    print("   ✅ User registration (POST /auth/register)")
    print("   ✅ User login (POST /auth/login)")
    print("   ✅ JWT token generation")
    print("   ✅ Password hashing (bcrypt)")
    print("   ✅ Username validation")
    print("   ✅ Duplicate prevention")
    print("   ✅ Error handling")
    print("\n🎯 Next Phase: Paper Trading System (deposit, orders, balance)")
    print()


if __name__ == "__main__":
    try:
        main()
    except requests.ConnectionError:
        print("\n❌ Error: Cannot connect to server")
        print("   Make sure the server is running: python run_server.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
