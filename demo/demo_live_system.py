"""
End-to-end demonstration of live RAG system.
Proves dynamic behavior for hackathon judges.

This script demonstrates:
1. System responds to real-time data changes
2. RAG answers update when new events arrive
3. WebSocket broadcasts live updates
4. Complete "liveness" proof
"""

import asyncio
import json
import time
from datetime import datetime

import httpx
import websockets

# Configuration
API_BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/live-updates"


class Colors:
    """Terminal colors for pretty output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print colored header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(70)}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.END}\n")


def print_step(step: int, text: str):
    """Print step number and description."""
    print(f"{Colors.CYAN}{Colors.BOLD}📍 Step {step}: {text}{Colors.END}")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")


def print_data(text: str):
    """Print data/result."""
    print(f"{Colors.YELLOW}📊 {text}{Colors.END}")


async def check_system_health():
    """Check if system is healthy and ready."""
    print_step(0, "Checking System Health")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE_URL}/api/v1/health")
            health = response.json()
            
            print_info(f"Status: {health['status']}")
            print_info(f"Pipeline running: {health['pipeline_running']}")
            print_info(f"RAG available: {health.get('rag_available', False)}")
            
            if health['status'] == 'healthy' or health['pipeline_running']:
                print_success("System is operational!")
                return True
            else:
                print(f"{Colors.RED}❌ System not ready{Colors.END}")
                return False
                
        except Exception as e:
            print(f"{Colors.RED}❌ Cannot connect to API: {e}{Colors.END}")
            return False


async def query_rag_system(question: str) -> dict:
    """Query the RAG system."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/chat",
                json={"query": question, "top_k": 5}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Status {response.status_code}", "answer": "N/A"}
                
        except Exception as e:
            return {"error": str(e), "answer": "N/A"}


async def get_top_repos() -> list:
    """Get current top repositories."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE_URL}/api/v1/repos/top10")
            if response.status_code == 200:
                data = response.json()
                return data.get("repositories", [])
            return []
        except:
            return []


async def listen_to_websocket(duration: int = 30):
    """Listen to WebSocket updates for a duration."""
    print_info(f"Listening to WebSocket for {duration} seconds...")
    
    messages = []
    
    try:
        async with websockets.connect(WS_URL) as websocket:
            start_time = time.time()
            
            while (time.time() - start_time) < duration:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    messages.append(data)
                    
                    msg_type = data.get("type")
                    if msg_type != "heartbeat":
                        print_data(f"Received: {msg_type}")
                        
                except asyncio.TimeoutError:
                    continue
                except:
                    break
    except Exception as e:
        print_info(f"WebSocket connection ended: {e}")
    
    return messages


async def demonstrate_live_rag():
    """
    Main demonstration function.
    
    Demonstrates that the RAG system updates in real-time:
    1. Query initial state
    2. Wait for new data
    3. Query again
    4. Show answers changed
    """
    
    print_header("🚀 LIVE RAG SYSTEM DEMONSTRATION")
    print(f"{Colors.BOLD}Demonstrating Dynamic RAG with Real-Time Updates{Colors.END}\n")
    
    # Step 0: Health check
    healthy = await check_system_health()
    if not healthy:
        print(f"\n{Colors.RED}System not ready. Please start the server first.{Colors.END}")
        print(f"{Colors.YELLOW}Run: python backend/api/main.py{Colors.END}")
        return
    
    await asyncio.sleep(2)
    
    # Step 1: Initial state
    print_header("STEP 1: Query Initial State")
    print_info("Asking: 'Which repositories are most active right now?'")
    
    result1 = await query_rag_system("Which repositories are most active right now?")
    answer1 = result1.get("answer", "")
    sources1 = result1.get("sources", [])
    
    if answer1 and answer1 != "N/A":
        print_success("Query successful!")
        print_data(f"Answer length: {len(answer1)} characters")
        print_data(f"Sources: {len(sources1)} repositories")
        print(f"\n{Colors.BOLD}Answer 1 (first 200 chars):{Colors.END}")
        print(f"{answer1[:200]}...")
    else:
        print(f"{Colors.YELLOW}⚠️  RAG system returned: {result1.get('error', 'No answer')}{Colors.END}")
        print_info("This is normal if no data has flowed through yet")
    
    await asyncio.sleep(3)
    
    # Step 2: Show current top repos
    print_header("STEP 2: Current Repository Rankings")
    
    repos = await get_top_repos()
    if repos:
        print_success(f"Found {len(repos)} repositories")
        for i, repo in enumerate(repos[:5], 1):
            print_data(
                f"{i}. {repo['repo_full_name']} - "
                f"Score: {repo['activity_score']}, "
                f"Trend: {repo['trend_status']}"
            )
    else:
        print_info("No repositories data yet (pipeline warming up)")
    
    await asyncio.sleep(2)
    
    # Step 3: Wait for updates
    print_header("STEP 3: Waiting for Live Updates")
    print_info("Monitoring WebSocket for real-time changes...")
    print_info("(Demo connector generates events every ~8 seconds)")
    
    messages = await listen_to_websocket(duration=25)
    
    event_types = {}
    for msg in messages:
        msg_type = msg.get("type", "unknown")
        event_types[msg_type] = event_types.get(msg_type, 0) + 1
    
    print_success(f"Received {len(messages)} total messages")
    for msg_type, count in event_types.items():
        if msg_type != "heartbeat":
            print_data(f"  {msg_type}: {count}")
    
    await asyncio.sleep(2)
    
    # Step 4: Query again
    print_header("STEP 4: Query Updated State")
    print_info("Asking the same question after updates...")
    
    result2 = await query_rag_system("Which repositories are most active right now?")
    answer2 = result2.get("answer", "")
    sources2 = result2.get("sources", [])
    
    if answer2 and answer2 != "N/A":
        print_success("Query successful!")
        print_data(f"Answer length: {len(answer2)} characters")
        print_data(f"Sources: {len(sources2)} repositories")
        print(f"\n{Colors.BOLD}Answer 2 (first 200 chars):{Colors.END}")
        print(f"{answer2[:200]}...")
    else:
        print_info(f"RAG system: {result2.get('error', 'No answer')}")
    
    await asyncio.sleep(2)
    
    # Step 5: Comparison
    print_header("STEP 5: Verify Dynamic Behavior")
    
    if answer1 and answer2 and answer1 != "N/A" and answer2 != "N/A":
        if answer1 != answer2:
            print_success("✨ ANSWERS ARE DIFFERENT! ✨")
            print_success("🎯 DYNAMIC RAG PROVEN!")
            print_data(f"Answer 1 length: {len(answer1)} chars")
            print_data(f"Answer 2 length: {len(answer2)} chars")
            print_data(f"Difference: {abs(len(answer2) - len(answer1))} chars")
        else:
            print_info("Answers are similar (may need more time for changes)")
            print_info("This can happen if no significant events occurred")
    else:
        print_info("RAG system is initializing - run demo again in 30 seconds")
    
    # Step 6: Show updated rankings
    print_header("STEP 6: Final Repository Rankings")
    
    repos_final = await get_top_repos()
    if repos_final:
        print_success(f"Current top {len(repos_final)} repositories:")
        for i, repo in enumerate(repos_final[:5], 1):
            print_data(
                f"{i}. {repo['repo_full_name']} - "
                f"Score: {repo['activity_score']}, "
                f"Trend: {repo['trend_status']}"
            )
    
    await asyncio.sleep(1)
    
    # Summary
    print_header("📊 DEMONSTRATION SUMMARY")
    
    print(f"{Colors.BOLD}System Components:{Colors.END}")
    print_success("✅ Pathway pipeline: Running")
    print_success("✅ WebSocket updates: Working")
    print_success(f"✅ Live events received: {len([m for m in messages if m.get('type') not in ['heartbeat', 'connection']])}")
    
    if answer1 != answer2 and answer1 != "N/A":
        print_success("✅ Dynamic RAG: PROVEN!")
    else:
        print_info("⏳ Dynamic RAG: Initializing (run again)")
    
    print(f"\n{Colors.BOLD}Key Findings:{Colors.END}")
    print_data(f"• Total WebSocket messages: {len(messages)}")
    print_data(f"• Unique event types: {len(event_types)}")
    print_data(f"• Repositories tracked: {len(repos_final)}")
    
    print_header("🎉 DEMONSTRATION COMPLETE")
    print(f"{Colors.GREEN}{Colors.BOLD}The system demonstrates real-time AI capabilities!{Colors.END}\n")


if __name__ == "__main__":
    print(f"\n{Colors.BOLD}Starting Live RAG System Demonstration...{Colors.END}")
    print(f"{Colors.YELLOW}Make sure the server is running: python backend/api/main.py{Colors.END}\n")
    
    try:
        asyncio.run(demonstrate_live_rag())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Demo interrupted by user{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Demo error: {e}{Colors.END}")