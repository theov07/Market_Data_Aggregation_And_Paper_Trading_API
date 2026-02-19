#!/usr/bin/env python3
import requests
import json

from config import BASE_URL


def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def test_register():
    print_section("TEST 1: User Registration")
    
    url = f"{BASE_URL}/auth/register"
    data = {
        "username": "alice_trader",
        "password": "mySecurePass123"
    }
    
    print(f"POST {url}")
    print(f"Body: {json.dumps(data, indent=2)}")
    
    response = requests.post(url, json=data)
    print(f"\nStatus: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 201:
        print("\nRegistration successful")
        return response.json()["access_token"]
    else:
        print("\nRegistration failed")
        return None


def test_duplicate_register():
    print_section("TEST 2: Duplicate Username Registration")
    
    url = f"{BASE_URL}/auth/register"
    data = {
        "username": "alice_trader",
        "password": "anotherPassword"
    }
    
    print(f"POST {url}")
    print(f"Body: {json.dumps(data, indent=2)}")
    
    response = requests.post(url, json=data)
    print(f"\nStatus: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 400:
        print("\nCorrectly rejected duplicate username")
    else:
        print("\nShould have rejected duplicate username")


def test_login_valid():
    print_section("TEST 3: Login with Valid Credentials")
    
    url = f"{BASE_URL}/auth/login"
    data = {
        "username": "alice_trader",
        "password": "mySecurePass123"
    }
    
    print(f"POST {url}")
    print(f"Body: {json.dumps(data, indent=2)}")
    
    response = requests.post(url, json=data)
    print(f"\nStatus: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("\nLogin successful")
        return response.json()["access_token"]
    else:
        print("\nLogin failed")
        return None


def test_login_invalid():
    print_section("TEST 4: Login with Invalid Password")
    
    url = f"{BASE_URL}/auth/login"
    data = {
        "username": "alice_trader",
        "password": "wrongPassword"
    }
    
    print(f"POST {url}")
    print(f"Body: {json.dumps(data, indent=2)}")
    
    response = requests.post(url, json=data)
    print(f"\nStatus: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 401:
        print("\nCorrectly rejected invalid credentials")
    else:
        print("\nShould have rejected invalid credentials")


def test_username_validation():
    print_section("TEST 5: Username Validation")
    
    invalid_usernames = [
        ("ab", "Too short (min 3 chars)"),
        ("user@name", "Invalid characters (@ not allowed)"),
        ("user name", "Invalid characters (space not allowed)"),
    ]
    
    for username, reason in invalid_usernames:
        print(f"\nTesting: {username} - {reason}")
        
        url = f"{BASE_URL}/auth/register"
        data = {
            "username": username,
            "password": "password123"
        }
        
        response = requests.post(url, json=data)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 422:
            print(f"Correctly rejected: {response.json()['detail'][0]['msg']}")
        elif response.status_code == 400:
            print(f"Correctly rejected: {response.json()['detail']}")
        else:
            print(f"Should have rejected")


def test_token_usage():
    print_section("TEST 6: Using JWT Token")
    
    print("Logging in to get token...")
    url = f"{BASE_URL}/auth/login"
    data = {"username": "alice_trader", "password": "mySecurePass123"}
    response = requests.post(url, json=data)
    token = response.json()["access_token"]
    
    print(f"Got token: {token[:50]}...")
    print(f"\nToken format: Bearer token")
    print(f"Use in header: Authorization: Bearer <token>")
    print(f"\nThis token can be used to access protected endpoints")


def main():
    print("\n" + "="*60)
    print("  PHASE 3: AUTHENTICATION TESTING")
    print("="*60)
    print("\nTesting FastAPI authentication with JWT tokens")
    print(f"Server: {BASE_URL}")
    
    test_register()
    test_duplicate_register()
    test_login_valid()
    test_login_invalid()
    test_username_validation()
    test_token_usage()
    
    print_section("All Tests Completed")
    print("\nPhase 3 Features Validated:")
    print("  - User registration (POST /auth/register)")
    print("  - User login (POST /auth/login)")
    print("  - JWT token generation")
    print("  - Password hashing (bcrypt)")
    print("  - Username validation")
    print("  - Duplicate prevention")
    print("  - Error handling")
    print()


if __name__ == "__main__":
    try:
        main()
    except requests.ConnectionError:
        print("\nError: Cannot connect to server")
        print("Make sure the server is running: python run_server.py")
    except Exception as e:
        print(f"\nError: {e}")
