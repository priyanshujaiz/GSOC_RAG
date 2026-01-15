# 🌐 WebSocket Integration Guide

**Live Open-Source Intelligence Platform**  
**Real-Time Updates via WebSocket**  
**Last Updated:** January 15, 2026

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Connection Setup](#connection-setup)
3. [Message Types](#message-types)
4. [Client Implementation](#client-implementation)
5. [Message Handling](#message-handling)
6. [Connection Management](#connection-management)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)
9. [Examples](#examples)

---

## 🎯 Overview

The WebSocket endpoint provides **real-time push notifications** when repository data changes. Instead of polling the REST API repeatedly, clients can maintain a persistent connection and receive updates instantly.

### **Key Features**
- ✅ **Real-time updates** - Instant notifications of new events, ranking changes, trends
- ✅ **Low latency** - Typically < 100ms from event to notification
- ✅ **Efficient** - Single connection, no polling overhead
- ✅ **Heartbeat** - Automatic keep-alive every 30 seconds
- ✅ **Ping/Pong** - Health check mechanism
- ✅ **Multiple clients** - Broadcast to all connected clients

### **Use Cases**
- 📊 Live dashboards with auto-updating charts
- 🔔 Real-time notification systems
- 📱 Mobile apps with push notifications
- 🤖 Monitoring bots and alerting systems
- 🎮 Collaborative tools with shared state

---

## 🔌 Connection Setup

### **WebSocket Endpoint**
```
ws://localhost:8000/ws/live-updates
```

For production with SSL:
```
wss://your-domain.com/ws/live-updates
```

### **Connection Flow**

```
1. Client initiates WebSocket connection
   ↓
2. Server accepts connection
   ↓
3. Server sends connection confirmation message
   ↓
4. Server starts heartbeat loop (30s interval)
   ↓
5. Client receives real-time updates
   ↓
6. Client can send ping → Server responds pong
   ↓
7. On disconnect: Server cleans up resources
```

---

## 📨 Message Types

All messages are JSON objects with a `type` field and a `timestamp` field.

### **1. Connection Message**

Sent immediately upon successful connection.

```json
{
  "type": "connection",
  "status": "connected",
  "client_id": "client_138669891834384",
  "message": "Connected to live updates",
  "timestamp": "2026-01-15T10:30:00.123456"
}
```

**When:** Once, immediately after connection  
**Action:** Store `client_id` for debugging

---

### **2. Heartbeat Message**

Keep-alive message to prevent connection timeouts.

```json
{
  "type": "heartbeat",
  "timestamp": "2026-01-15T10:30:30.123456"
}
```

**When:** Every 30 seconds  
**Action:** No action needed (handled automatically)

---

### **3. New Event Message**

Notifies when a new GitHub event is detected.

```json
{
  "type": "new_event",
  "timestamp": "2026-01-15T10:30:05.123456",
  "event_id": "commit_abc123",
  "repo_full_name": "openai/openai-python",
  "event_type": "commit",
  "title": "Fix bug in chat completion",
  "author": "alice",
  "url": "https://github.com/openai/openai-python/commit/abc123",
  "data": {
    "additions": 45,
    "deletions": 12,
    "files_changed": 3
  }
}
```

**When:** New GitHub event processed by pipeline  
**Action:** Display notification, update event feed, increment counters

---

### **4. Summary Update Message**

Notifies when a repository's summary changes.

```json
{
  "type": "summary_update",
  "timestamp": "2026-01-15T10:30:10.123456",
  "repo_full_name": "openai/openai-python",
  "summary": "High activity with 45 events in 24h. Recent focus on API improvements and bug fixes.",
  "activity_score": 18.5,
  "trend_status": "🔥 HOT",
  "momentum": "ACCELERATING",
  "events_in_window": 45
}
```

**When:** Repository summary recalculated (new data causes content change)  
**Action:** Update repository card, refresh summary text

---

### **5. Ranking Change Message**

Notifies when a repository's rank in Top 10 changes.

```json
{
  "type": "ranking_change",
  "timestamp": "2026-01-15T10:30:15.123456",
  "repo_full_name": "langchain-ai/langchain",
  "old_rank": 3,
  "new_rank": 1,
  "activity_score": 25.5,
  "change": "up"
}
```

**When:** Repository moves position in Top 10 rankings  
**Action:** Update leaderboard, highlight change, show animation  
**Change values:** `"up"`, `"down"`, `"new"` (entered Top 10), `"dropped"` (left Top 10)

---

### **6. Trend Change Message**

Notifies when a repository's trend status changes.

```json
{
  "type": "trend_change",
  "timestamp": "2026-01-15T10:30:20.123456",
  "repo_full_name": "pathwaycom/pathway",
  "old_status": "📈 ACTIVE",
  "new_status": "🔥 HOT",
  "momentum": "ACCELERATING",
  "velocity": 2.8,
  "activity_score": 22.3
}
```

**When:** Trend detector identifies status change (STABLE → ACTIVE → HOT or vice versa)  
**Action:** Update trend indicator, show trend badge, trigger alert

**Trend Status Values:**
- `"🔥 HOT"` - High activity and accelerating
- `"📈 ACTIVE"` - Moderate activity with growth
- `"📊 STABLE"` - Consistent activity
- `"📉 COOLING"` - Decreasing activity
- `"💤 QUIET"` - Low activity

---

### **7. Metrics Update Message**

Notifies when global system metrics change.

```json
{
  "type": "metrics_update",
  "timestamp": "2026-01-15T10:30:25.123456",
  "total_events": 1523,
  "active_repositories": 42,
  "total_queries": 89,
  "websocket_connections": 5,
  "changes": {
    "total_events": "+5",
    "active_repositories": "+1"
  }
}
```

**When:** Every 5 seconds if metrics changed  
**Action:** Update dashboard stats, refresh counters

---

### **8. System Status Message**

Notifies when system health status changes.

```json
{
  "type": "system_status",
  "timestamp": "2026-01-15T10:30:30.123456",
  "status": "healthy",
  "components": {
    "api": "operational",
    "pipeline": "running",
    "rag": "available"
  },
  "message": "All systems operational",
  "severity": "info"
}
```

**When:** System health changes (e.g., pipeline stops, RAG becomes unavailable)  
**Action:** Show status banner, log event  
**Severity values:** `"info"`, `"warning"`, `"error"`, `"critical"`

---

### **9. Error Message**

Notifies when an error occurs.

```json
{
  "type": "error",
  "timestamp": "2026-01-15T10:30:35.123456",
  "error_code": "PIPELINE_ERROR",
  "message": "Failed to process event batch",
  "severity": "warning",
  "details": {
    "affected_repos": ["openai/openai-python"],
    "retry_in_seconds": 60
  }
}
```

**When:** Errors during data processing or broadcasting  
**Action:** Log error, show notification to user, retry if applicable

---

### **10. Pong Message**

Response to client ping (for connection health checks).

```json
{
  "type": "pong",
  "timestamp": "2026-01-15T10:30:40.123456"
}
```

**When:** Client sends `{"type": "ping"}`  
**Action:** Measure round-trip time, verify connection alive

---

## 💻 Client Implementation

### **Python with websockets**

```python
import asyncio
import json
import websockets

async def connect_to_updates():
    uri = "ws://localhost:8000/ws/live-updates"
    
    async with websockets.connect(uri) as websocket:
        print("✅ Connected to live updates")
        
        # Receive messages
        async for message in websocket:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "connection":
                print(f"Connected with ID: {data['client_id']}")
            
            elif message_type == "heartbeat":
                print("💓 Heartbeat")
            
            elif message_type == "new_event":
                print(f"📨 New {data['event_type']}: {data['title']}")
            
            elif message_type == "ranking_change":
                print(f"📊 {data['repo_full_name']}: {data['old_rank']} → {data['new_rank']}")
            
            elif message_type == "summary_update":
                print(f"📝 Summary updated: {data['repo_full_name']}")

# Run
asyncio.run(connect_to_updates())
```

### **Python with WebSocket Library (Advanced)**

```python
import asyncio
import json
from typing import Callable, Dict
import websockets

class LiveUpdatesClient:
    def __init__(self, uri: str = "ws://localhost:8000/ws/live-updates"):
        self.uri = uri
        self.websocket = None
        self.handlers: Dict[str, Callable] = {}
        self.client_id = None
        self.connected = False
    
    def on(self, message_type: str, handler: Callable):
        """Register a message handler."""
        self.handlers[message_type] = handler
    
    async def connect(self):
        """Connect to WebSocket."""
        self.websocket = await websockets.connect(self.uri)
        self.connected = True
        print("✅ Connected to live updates")
        
        # Start receiving messages
        asyncio.create_task(self._receive_messages())
    
    async def _receive_messages(self):
        """Receive and handle messages."""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                message_type = data.get("type")
                
                # Store client ID
                if message_type == "connection":
                    self.client_id = data.get("client_id")
                
                # Call registered handler
                if message_type in self.handlers:
                    await self.handlers[message_type](data)
        
        except websockets.exceptions.ConnectionClosed:
            print("❌ Connection closed")
            self.connected = False
    
    async def ping(self):
        """Send ping to check connection."""
        if self.connected:
            await self.websocket.send(json.dumps({"type": "ping"}))
    
    async def close(self):
        """Close connection."""
        if self.websocket:
            await self.websocket.close()
        self.connected = False

# Usage
async def main():
    client = LiveUpdatesClient()
    
    # Register handlers
    client.on("new_event", lambda data: print(f"📨 {data['title']}"))
    client.on("ranking_change", lambda data: print(f"📊 Rank change: {data['repo_full_name']}"))
    
    # Connect
    await client.connect()
    
    # Keep running
    while client.connected:
        await asyncio.sleep(1)

asyncio.run(main())
```

### **JavaScript/TypeScript (Browser)**

```javascript
class LiveUpdatesClient {
  constructor(url = 'ws://localhost:8000/ws/live-updates') {
    this.url = url;
    this.ws = null;
    this.handlers = {};
    this.clientId = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log('✅ Connected to live updates');
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const type = data.type;

      // Store client ID
      if (type === 'connection') {
        this.clientId = data.client_id;
      }

      // Call registered handler
      if (this.handlers[type]) {
        this.handlers[type](data);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('❌ Connection closed');
      this.attemptReconnect();
    };
  }

  on(type, handler) {
    this.handlers[type] = handler;
  }

  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  ping() {
    this.send({ type: 'ping' });
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
      console.log(`Reconnecting in ${delay}ms...`);
      setTimeout(() => this.connect(), delay);
    }
  }

  close() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// Usage
const client = new LiveUpdatesClient();

client.on('new_event', (data) => {
  console.log(`📨 New ${data.event_type}: ${data.title}`);
  // Update UI
  addEventToFeed(data);
});

client.on('ranking_change', (data) => {
  console.log(`📊 ${data.repo_full_name}: ${data.old_rank} → ${data.new_rank}`);
  // Update leaderboard
  updateRanking(data);
});

client.on('summary_update', (data) => {
  console.log(`📝 Summary updated: ${data.repo_full_name}`);
  // Refresh repository card
  refreshRepoCard(data.repo_full_name);
});

client.connect();
```

### **React Hook (TypeScript)**

```typescript
import { useEffect, useRef, useState } from 'react';

interface WebSocketMessage {
  type: string;
  timestamp: string;
  [key: string]: any;
}

type MessageHandler = (data: WebSocketMessage) => void;

export function useLiveUpdates(url: string = 'ws://localhost:8000/ws/live-updates') {
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const handlersRef = useRef<Record<string, MessageHandler>>({});

  useEffect(() => {
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('Connected');
      setConnected(true);
    };

    ws.onmessage = (event) => {
      const data: WebSocketMessage = JSON.parse(event.data);
      setMessages((prev) => [...prev, data]);

      // Call handler if registered
      const handler = handlersRef.current[data.type];
      if (handler) {
        handler(data);
      }
    };

    ws.onclose = () => {
      console.log('Disconnected');
      setConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [url]);

  const on = (type: string, handler: MessageHandler) => {
    handlersRef.current[type] = handler;
  };

  const send = (message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  };

  return { connected, messages, on, send };
}

// Usage in component
function Dashboard() {
  const { connected, on } = useLiveUpdates();
  const [events, setEvents] = useState([]);

  useEffect(() => {
    on('new_event', (data) => {
      setEvents((prev) => [data, ...prev].slice(0, 50));
    });
  }, [on]);

  return (
    <div>
      <div>Status: {connected ? '🟢 Connected' : '🔴 Disconnected'}</div>
      <div>Recent Events: {events.length}</div>
      {events.map((event) => (
        <div key={event.event_id}>{event.title}</div>
      ))}
    </div>
  );
}
```

---

## 🔧 Message Handling

### **Recommended Handler Structure**

```python
async def handle_message(data: dict):
    """Central message handler."""
    message_type = data.get("type")
    
    handlers = {
        "connection": handle_connection,
        "heartbeat": handle_heartbeat,
        "new_event": handle_new_event,
        "summary_update": handle_summary_update,
        "ranking_change": handle_ranking_change,
        "trend_change": handle_trend_change,
        "metrics_update": handle_metrics_update,
        "system_status": handle_system_status,
        "error": handle_error,
        "pong": handle_pong,
    }
    
    handler = handlers.get(message_type)
    if handler:
        await handler(data)
    else:
        print(f"Unknown message type: {message_type}")

async def handle_new_event(data: dict):
    """Handle new event."""
    print(f"📨 New {data['event_type']}: {data['title']}")
    # Add to event feed
    # Send notification
    # Update counters

async def handle_ranking_change(data: dict):
    """Handle ranking change."""
    change_emoji = "⬆️" if data["change"] == "up" else "⬇️"
    print(f"{change_emoji} {data['repo_full_name']}: #{data['old_rank']} → #{data['new_rank']}")
    # Update leaderboard
    # Animate change
```

---

## 🔄 Connection Management

### **Heartbeat & Keep-Alive**

The server sends heartbeat messages every 30 seconds. Clients should:

1. **Monitor heartbeats** - Track time since last heartbeat
2. **Detect timeouts** - If no message in 60 seconds, assume connection dead
3. **Reconnect** - Implement exponential backoff

```python
import time

last_heartbeat = time.time()

async def monitor_connection():
    while True:
        await asyncio.sleep(10)
        
        if time.time() - last_heartbeat > 60:
            print("⚠️ Connection timeout detected")
            # Attempt reconnect
            await reconnect()

async def handle_heartbeat(data: dict):
    global last_heartbeat
    last_heartbeat = time.time()
```

### **Ping/Pong for Health Checks**

Clients can send ping to verify connection:

```python
async def check_connection_health():
    """Ping server and measure response time."""
    start = time.time()
    await websocket.send(json.dumps({"type": "ping"}))
    
    # Wait for pong (with timeout)
    try:
        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
        data = json.loads(message)
        if data.get("type") == "pong":
            latency = (time.time() - start) * 1000
            print(f"Pong received in {latency:.2f}ms")
            return True
    except asyncio.TimeoutError:
        print("Ping timeout")
        return False
```

### **Reconnection Strategy**

```python
class ReconnectingWebSocket:
    def __init__(self, uri: str):
        self.uri = uri
        self.max_retries = 10
        self.base_delay = 1  # seconds
    
    async def connect_with_retry(self):
        for attempt in range(self.max_retries):
            try:
                websocket = await websockets.connect(self.uri)
                print(f"✅ Connected (attempt {attempt + 1})")
                return websocket
            
            except Exception as e:
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), 60)
                    print(f"⚠️ Connection failed, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    print(f"❌ Failed after {self.max_retries} attempts")
                    raise
```

---

## ✅ Best Practices

### **1. Handle All Message Types**

Always implement handlers for all message types, even if just logging:

```python
# ❌ Bad: Ignoring unknown messages
if message_type == "new_event":
    handle_event(data)

# ✅ Good: Default handler
handlers.get(message_type, handle_unknown)(data)
```

### **2. Validate Messages**

Don't assume message structure is correct:

```python
# ✅ Good: Validate before using
def handle_new_event(data: dict):
    required_fields = ["event_id", "repo_full_name", "event_type"]
    if not all(field in data for field in required_fields):
        logger.error(f"Invalid new_event message: {data}")
        return
    
    # Process...
```

### **3. Implement Reconnection**

Network issues are common - always implement automatic reconnection with exponential backoff.

### **4. Rate Limit UI Updates**

Don't update UI on every message - batch updates:

```javascript
let pendingUpdates = [];

client.on('new_event', (data) => {
  pendingUpdates.push(data);
});

setInterval(() => {
  if (pendingUpdates.length > 0) {
    updateUI(pendingUpdates);
    pendingUpdates = [];
  }
}, 1000); // Update UI every 1 second
```

### **5. Monitor Connection Health**

Track heartbeats and implement ping/pong checks.

### **6. Handle Errors Gracefully**

```python
try:
    async for message in websocket:
        await handle_message(json.loads(message))
except websockets.exceptions.ConnectionClosed:
    print("Connection closed, attempting reconnect...")
    await reconnect()
except json.JSONDecodeError:
    print("Invalid JSON received")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### **7. Clean Up Resources**

Always close connections properly:

```python
try:
    # Use websocket
    pass
finally:
    await websocket.close()
```

---

## 🐛 Troubleshooting

### **Connection Refused**

**Symptoms:** Can't connect to WebSocket

**Causes:**
- Server not running
- Wrong URL/port
- Firewall blocking connection

**Solutions:**
```bash
# Check if server is running
curl http://localhost:8000/health

# Check WebSocket stats
curl http://localhost:8000/ws/stats

# Test with simple client
python -c "import websockets; import asyncio; asyncio.run(websockets.connect('ws://localhost:8000/ws/live-updates'))"
```

### **Connection Drops**

**Symptoms:** Connection closes unexpectedly

**Causes:**
- Network issues
- Server restart
- Missed heartbeats
- Firewall timeout

**Solutions:**
- Implement reconnection logic
- Monitor heartbeats
- Use ping/pong
- Increase timeout settings

### **No Messages Received**

**Symptoms:** Connected but no updates

**Causes:**
- No data flowing through pipeline
- DEMO_MODE not enabled
- Pipeline not running

**Solutions:**
```bash
# Check pipeline status
curl http://localhost:8000/api/v1/health | jq '.components.pathway_pipeline'

# Enable DEMO mode
export DEMO_MODE=true
```

### **High Memory Usage**

**Symptoms:** Client memory grows over time

**Causes:**
- Not cleaning up old messages
- Memory leaks in handlers

**Solutions:**
```python
# Limit stored messages
MAX_MESSAGES = 1000
messages = messages[-MAX_MESSAGES:]  # Keep only recent
```

---

## 📚 Examples

### **Example 1: Simple Event Monitor**

```python
import asyncio
import json
import websockets

async def monitor_events():
    uri = "ws://localhost:8000/ws/live-updates"
    async with websockets.connect(uri) as ws:
        async for message in ws:
            data = json.loads(message)
            if data["type"] == "new_event":
                print(f"📨 {data['event_type']}: {data['title']}")

asyncio.run(monitor_events())
```

### **Example 2: Live Dashboard Counter**

```python
import asyncio
import json
import websockets
from collections import Counter

event_counter = Counter()

async def count_events():
    uri = "ws://localhost:8000/ws/live-updates"
    
    async with websockets.connect(uri) as ws:
        async for message in ws:
            data = json.loads(message)
            
            if data["type"] == "new_event":
                event_type = data["event_type"]
                event_counter[event_type] += 1
                
                print(f"\rCommits: {event_counter['commit']} | "
                      f"PRs: {event_counter['pull_request']} | "
                      f"Issues: {event_counter['issue']}", end="")

asyncio.run(count_events())
```

### **Example 3: Ranking Change Alert**

```python
import asyncio
import json
import websockets

async def alert_on_big_changes():
    uri = "ws://localhost:8000/ws/live-updates"
    
    async with websockets.connect(uri) as ws:
        async for message in ws:
            data = json.loads(message)
            
            if data["type"] == "ranking_change":
                rank_diff = abs(data["new_rank"] - data["old_rank"])
                
                if rank_diff >= 3:  # Big jump
                    print(f"🚨 BIG CHANGE: {data['repo_full_name']} "
                          f"moved {rank_diff} positions!")
                    # Send alert (email, Slack, etc.)

asyncio.run(alert_on_big_changes())
```

---

## 🔗 Additional Resources

- **API Documentation:** See `API_GUIDE.md`
- **Server Code:** `backend/api/routes/websocket.py`
- **Message Models:** `backend/api/models/websocket_events.py`
- **Live Demo:** `demo/demo_live_system.py`

---

## 📞 Support

For issues or questions:
- Open an issue on GitHub
- Contact: your-email@example.com

---

**Last Updated:** January 15, 2026  
**WebSocket Endpoint:** `/ws/live-updates`  
**Protocol Version:** 1.0.0

