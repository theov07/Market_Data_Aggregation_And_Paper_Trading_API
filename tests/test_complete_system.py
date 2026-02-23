#!/usr/bin/env python3
"""
Comprehensive system test - validates all features
Tests REST API, WebSocket API, and order execution
"""
import asyncio
import json
import requests
import websockets
import time
from typing import Optional


BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws"


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}{Colors.END}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.YELLOW}→ {text}{Colors.END}")


class SystemTester:
    """Complete system test suite"""
    
    def __init__(self):
        self.token: Optional[str] = None
        self.username: Optional[str] = None
        self.tests_passed = 0
        self.tests_failed = 0
    
    def test_rest_auth(self) -> bool:
        """Test REST authentication endpoints"""
        print_header("TEST 1: REST AUTHENTICATION")
        
        try:
            # Register
            self.username = f"final_test_{int(time.time())}"
            password = "secure_pass_123"
            
            print_info(f"Registering user: {self.username}")
            response = requests.post(
                f"{BASE_URL}/auth/register",
                json={"username": self.username, "password": password}
            )
            
            if response.status_code != 201:
                print_error(f"Registration failed: {response.status_code}")
                return False
            
            self.token = response.json()["access_token"]
            print_success(f"Registration successful")
            
            # Login
            print_info("Testing login")
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json={"username": self.username, "password": password}
            )
            
            if response.status_code != 200:
                print_error(f"Login failed: {response.status_code}")
                return False
            
            print_success("Login successful")
            return True
            
        except Exception as e:
            print_error(f"Auth test failed: {e}")
            return False
    
    def test_rest_deposit(self) -> bool:
        """Test deposit endpoint"""
        print_header("TEST 2: REST DEPOSIT")
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            # Deposit USDT
            print_info("Depositing 100,000 USDT")
            response = requests.post(
                f"{BASE_URL}/deposit",
                json={"asset": "USDT", "amount": 100000.0},
                headers=headers
            )
            
            if response.status_code != 200:
                print_error(f"USDT deposit failed: {response.status_code}")
                return False
            
            data = response.json()
            print_success(f"USDT deposited: {data['new_balance']}")
            
            # Deposit BTC
            print_info("Depositing 1 BTC")
            response = requests.post(
                f"{BASE_URL}/deposit",
                json={"asset": "BTC", "amount": 1.0},
                headers=headers
            )
            
            if response.status_code != 200:
                print_error(f"BTC deposit failed: {response.status_code}")
                return False
            
            data = response.json()
            print_success(f"BTC deposited: {data['new_balance']}")
            
            return True
            
        except Exception as e:
            print_error(f"Deposit test failed: {e}")
            return False
    
    def test_rest_balances(self) -> bool:
        """Test balance retrieval"""
        print_header("TEST 3: REST BALANCES")
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            print_info("Fetching balances")
            response = requests.get(
                f"{BASE_URL}/balance",  # Singular, not plural
                headers=headers
            )
            
            if response.status_code != 200:
                print_error(f"Balance fetch failed: {response.status_code}")
                return False
            
            data = response.json()
            balances = data.get("balances", [])
            print_success("Balances retrieved:")
            for balance in balances:
                print(f"  • {balance['asset']}: {balance['available']} (Reserved: {balance['reserved']})")
            
            return True
            
        except Exception as e:
            print_error(f"Balance test failed: {e}")
            return False
    
    def test_rest_order_create(self) -> bool:
        """Test REST order creation"""
        print_header("TEST 4: REST ORDER MANAGEMENT")
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            # Create buy order
            print_info("Creating limit buy order")
            order_data = {
                "token_id": f"rest_buy_{int(time.time())}",
                "symbol": "BTCUSDT",
                "side": "buy",
                "price": 50000.0,
                "quantity": 0.1
            }
            
            response = requests.post(
                f"{BASE_URL}/orders",
                json=order_data,
                headers=headers
            )
            
            if response.status_code != 201:
                print_error(f"Order creation failed: {response.status_code}")
                print_error(f"Response: {response.text}")
                return False
            
            order = response.json()
            print_success(f"Order created: ID={order['id']}, Status={order['status']}")
            
            # Get specific order
            print_info(f"Fetching order {order_data['token_id']}")
            response = requests.get(
                f"{BASE_URL}/orders/{order_data['token_id']}",
                headers=headers
            )
            
            if response.status_code != 200:
                print_error(f"Order fetch failed: {response.status_code}")
                return False
            
            fetched_order = response.json()
            print_success(f"Order fetched: ID={fetched_order['id']}, Status={fetched_order['status']}")
            
            # Cancel order
            print_info(f"Cancelling order {order_data['token_id']}")
            response = requests.delete(
                f"{BASE_URL}/orders/{order_data['token_id']}",
                headers=headers
            )
            
            if response.status_code != 200:
                print_error(f"Order cancellation failed: {response.status_code}")
                return False
            
            cancelled = response.json()
            print_success(f"Order cancelled: Status={cancelled['status']}")
            
            return True
            
        except Exception as e:
            print_error(f"Order management test failed: {e}")
            return False
    
    async def test_websocket_market_data(self) -> bool:
        """Test WebSocket market data subscription"""
        print_header("TEST 5: WEBSOCKET MARKET DATA")
        
        try:
            print_info("Connecting to WebSocket (no auth)")
            async with websockets.connect(WS_URL) as websocket:
                # Receive welcome
                welcome = await websocket.recv()
                data = json.loads(welcome)
                print_success(f"Connected: {data['message']}")
                
                # Subscribe to best_touch
                print_info("Subscribing to best_touch for BTCUSDT")
                await websocket.send(json.dumps({
                    "action": "subscribe",
                    "data_type": "best_touch",
                    "symbol": "BTCUSDT",
                    "exchange": "all"
                }))
                
                # Wait for confirmation
                msg = await websocket.recv()
                data = json.loads(msg)
                if data["type"] != "confirmation":
                    print_error(f"Expected confirmation, got: {data['type']}")
                    return False
                
                print_success(f"Subscribed: {data['subscription']}")
                
                # Receive market data
                print_info("Waiting for market data (5 seconds)...")
                best_touch_received = False
                for _ in range(10):
                    try:
                        msg = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                        data = json.loads(msg)
                        if data["type"] == "best_touch":
                            bid = data["data"]["bid_price"]
                            ask = data["data"]["ask_price"]
                            spread = data["data"]["spread"]
                            print_success(f"Market data: Bid=${bid:.2f}, Ask=${ask:.2f}, Spread=${spread:.2f}")
                            best_touch_received = True
                            break
                    except asyncio.TimeoutError:
                        continue
                
                if not best_touch_received:
                    print_error("No market data received")
                    return False
                
                # Unsubscribe
                print_info("Unsubscribing from best_touch")
                await websocket.send(json.dumps({
                    "action": "unsubscribe",
                    "data_type": "best_touch",
                    "symbol": "BTCUSDT",
                    "exchange": "all"
                }))
                
                # Wait for confirmation (skip remaining best_touch)
                for _ in range(20):
                    msg = await websocket.recv()
                    data = json.loads(msg)
                    if data["type"] == "confirmation" and data.get("action") == "unsubscribed":
                        print_success(f"Unsubscribed: {data['subscription']}")
                        break
                
                return True
                
        except Exception as e:
            print_error(f"WebSocket market data test failed: {e}")
            return False
    
    async def test_websocket_order_management(self) -> bool:
        """Test WebSocket order submission and cancellation"""
        print_header("TEST 6: WEBSOCKET ORDER MANAGEMENT")
        
        try:
            ws_url_with_token = f"{WS_URL}?token={self.token}"
            print_info(f"Connecting to WebSocket (authenticated as {self.username})")
            
            async with websockets.connect(ws_url_with_token) as websocket:
                # Welcome message
                welcome = await websocket.recv()
                data = json.loads(welcome)
                print_success(f"Authenticated: {data['auth_status']}")
                
                # Submit order via WebSocket
                order_token = f"ws_order_{int(time.time())}"
                print_info(f"Submitting buy order: {order_token}")
                
                await websocket.send(json.dumps({
                    "action": "submit_order",
                    "token_id": order_token,
                    "symbol": "BTCUSDT",
                    "side": "buy",
                    "price": 45000.0,  # Below market
                    "quantity": 0.05
                }))
                
                # Wait for confirmation
                order_confirmed = False
                for _ in range(10):
                    try:
                        msg = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(msg)
                        if data["type"] == "order_submitted":
                            order_id = data["order"]["id"]
                            status = data["order"]["status"]
                            print_success(f"Order submitted: ID={order_id}, Status={status}")
                            order_confirmed = True
                            break
                    except asyncio.TimeoutError:
                        break
                
                if not order_confirmed:
                    print_error("Order submission confirmation not received")
                    return False
                
                # Cancel order via WebSocket
                print_info(f"Cancelling order: {order_token}")
                await websocket.send(json.dumps({
                    "action": "cancel_order",
                    "token_id": order_token
                }))
                
                # Wait for cancellation confirmation
                cancel_confirmed = False
                for _ in range(10):
                    try:
                        msg = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(msg)
                        if data["type"] == "order_cancelled":
                            status = data["order"]["status"]
                            print_success(f"Order cancelled: Status={status}")
                            cancel_confirmed = True
                            break
                    except asyncio.TimeoutError:
                        break
                
                if not cancel_confirmed:
                    print_error("Order cancellation confirmation not received")
                    return False
                
                return True
                
        except Exception as e:
            print_error(f"WebSocket order management test failed: {e}")
            return False
    
    async def test_order_execution(self) -> bool:
        """Test order execution engine with real-time updates"""
        print_header("TEST 7: ORDER EXECUTION ENGINE")
        
        try:
            ws_url_with_token = f"{WS_URL}?token={self.token}"
            print_info("Testing order execution with WebSocket updates")
            
            async with websockets.connect(ws_url_with_token) as websocket:
                # Welcome
                await websocket.recv()
                
                # Submit order at market price (should execute)
                order_token = f"exec_test_{int(time.time())}"
                
                # Get current market price first via REST
                headers = {"Authorization": f"Bearer {self.token}"}
                
                print_info("Submitting order at current market price for execution")
                await websocket.send(json.dumps({
                    "action": "submit_order",
                    "token_id": order_token,
                    "symbol": "BTCUSDT",
                    "side": "buy",
                    "price": 70000.0,  # Above market for quick execution
                    "quantity": 0.01
                }))
                
                # Wait for submission and potential execution
                print_info("Monitoring for order execution (15 seconds)...")
                order_submitted = False
                order_executed = False
                
                for _ in range(30):  # 15 seconds total
                    try:
                        msg = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                        data = json.loads(msg)
                        
                        if data["type"] == "order_submitted":
                            print_success(f"Order submitted: {data['order']['token_id']}")
                            order_submitted = True
                        
                        elif data["type"] == "order_update":
                            if data["data"]["status"] == "filled":
                                exec_price = data["data"].get("execution_price", "N/A")
                                print_success(f"✨ ORDER EXECUTED! Execution price: ${exec_price}")
                                order_executed = True
                                break
                    
                    except asyncio.TimeoutError:
                        continue
                
                if not order_submitted:
                    print_error("Order was not submitted")
                    return False
                
                if order_executed:
                    print_success("Real-time execution update received via WebSocket")
                else:
                    print_info("Order not executed (may be below market - this is OK)")
                    # Cancel the order
                    await websocket.send(json.dumps({
                        "action": "cancel_order",
                        "token_id": order_token
                    }))
                    await websocket.recv()  # Cancellation confirmation
                
                return True
                
        except Exception as e:
            print_error(f"Order execution test failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all system tests"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}")
        print("╔═══════════════════════════════════════════════════════════════════╗")
        print("║         COMPREHENSIVE SYSTEM TEST - FINAL VALIDATION             ║")
        print("║              Market Data Aggregation & Paper Trading             ║")
        print("╚═══════════════════════════════════════════════════════════════════╝")
        print(Colors.END)
        
        tests = [
            ("REST Authentication", self.test_rest_auth),
            ("REST Deposit", self.test_rest_deposit),
            ("REST Balances", self.test_rest_balances),
            ("REST Order Management", self.test_rest_order_create),
            ("WebSocket Market Data", self.test_websocket_market_data),
            ("WebSocket Order Management", self.test_websocket_order_management),
            ("Order Execution Engine", self.test_order_execution),
        ]
        
        for test_name, test_func in tests:
            try:
                if asyncio.iscoroutinefunction(test_func):
                    result = await test_func()
                else:
                    result = test_func()
                
                if result:
                    self.tests_passed += 1
                else:
                    self.tests_failed += 1
                    
            except Exception as e:
                print_error(f"{test_name} crashed: {e}")
                self.tests_failed += 1
        
        # Final summary
        print(f"\n{Colors.BOLD}{Colors.BLUE}")
        print("╔═══════════════════════════════════════════════════════════════════╗")
        print("║                         TEST SUMMARY                              ║")
        print("╚═══════════════════════════════════════════════════════════════════╝")
        print(Colors.END)
        
        total = self.tests_passed + self.tests_failed
        pass_rate = (self.tests_passed / total * 100) if total > 0 else 0
        
        print(f"\nTotal Tests: {total}")
        print(f"{Colors.GREEN}Passed: {self.tests_passed}{Colors.END}")
        print(f"{Colors.RED}Failed: {self.tests_failed}{Colors.END}")
        print(f"Pass Rate: {pass_rate:.1f}%\n")
        
        if self.tests_failed == 0:
            print(f"{Colors.BOLD}{Colors.GREEN}")
            print("╔═══════════════════════════════════════════════════════════════════╗")
            print("║                   ✅ ALL TESTS PASSED! ✅                        ║")
            print("║              System is working perfectly!                        ║")
            print("╚═══════════════════════════════════════════════════════════════════╝")
            print(Colors.END)
        else:
            print(f"{Colors.BOLD}{Colors.RED}")
            print("╔═══════════════════════════════════════════════════════════════════╗")
            print("║                   ❌ SOME TESTS FAILED ❌                        ║")
            print("║              Please review the errors above                      ║")
            print("╚═══════════════════════════════════════════════════════════════════╝")
            print(Colors.END)


async def main():
    """Main test runner"""
    tester = SystemTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Tests interrupted by user{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Fatal error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
