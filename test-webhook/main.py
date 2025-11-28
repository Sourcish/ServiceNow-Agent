import os
from dotenv import load_dotenv
import functions_framework
from flask import jsonify
from google.auth import default
from google.auth.transport.requests import Request
import requests
import json
import uuid

# Load environment variables for local testing
load_dotenv()

PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT')
LOCATION = os.getenv('LOCATION', 'us-central1')
RESOURCE_ID = os.getenv('RESOURCE_ID')

# Build the base URL for Agent Engine
BASE_URL = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{RESOURCE_ID}"

# In-memory session storage
sessions = {}

def get_access_token():
    """Get Google Cloud access token automatically."""
    credentials, project = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    
    if not credentials.valid:
        credentials.refresh(Request())
    
    print(f"✅ Access token obtained")
    return credentials.token

def create_session(conversation_id: str, user_id: str = "teams-user") -> str:
    """Create a new Agent Engine session."""
    
    if conversation_id in sessions:
        print(f"♻️  Using existing session: {sessions[conversation_id]}")
        return sessions[conversation_id]
    
    try:
        access_token = get_access_token()
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        url = f"{BASE_URL}:query"
        
        payload = {
            "class_method": "create_session",
            "input": {
                "user_id": user_id
            }
        }
        
        print(f"📝 Creating session for conversation: {conversation_id}")
        print(f"🔗 URL: {url}")
        
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        print(f"📡 Session creation response status: {response.status_code}")
        
        response.raise_for_status()
        result = response.json()
        
        print(f"📦 Session response: {json.dumps(result, indent=2)}")
        
        session_id = result.get('output', {}).get('id')
        
        if not session_id:
            print(f"⚠️  No session ID in response, generating fallback")
            session_id = f"fallback-{uuid.uuid4()}"
        
        sessions[conversation_id] = session_id
        
        print(f"✅ Session created: {session_id}")
        return session_id
        
    except Exception as e:
        print(f"❌ Error creating session: {e}")
        import traceback
        traceback.print_exc()
        
        session_id = f"fallback-{uuid.uuid4()}"
        sessions[conversation_id] = session_id
        return session_id

def query_agent(session_id: str, user_message: str, user_id: str = "teams-user") -> str:
    """Query the Agent Engine agent."""
    
    try:
        access_token = get_access_token()
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        url = f"{BASE_URL}:streamQuery?alt=sse"
        
        payload = {
            "class_method": "stream_query",
            "input": {
                "user_id": user_id,
                "session_id": session_id,
                "message": user_message
            }
        }
        
        print(f"\n🔍 Querying agent...")
        print(f"🔗 URL: {url}")
        print(f"📝 Session ID: {session_id}")
        print(f"💬 Message: {user_message}")
        
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=60,
            stream=True
        )
        
        print(f"📡 Query response status: {response.status_code}")
        
        response.raise_for_status()
        
        full_response = ""
        
        print("📥 Reading SSE stream...")
        
        for line in response.iter_lines():
            if line:
                try:
                    line_text = line.decode('utf-8')
                    
                    # Remove SSE prefix
                    if line_text.startswith('data: '):
                        line_text = line_text[6:]
                    
                    # Skip empty lines and [DONE] marker
                    if not line_text.strip() or line_text.strip() == '[DONE]':
                        continue
                    
                    # Parse JSON
                    data = json.loads(line_text)
                    
                    # Show abbreviated event for debugging
                    event_preview = str(data)[:150]
                    print(f"📦 Event: {event_preview}...")
                    
                    # Extract text from content.parts array
                    if 'content' in data:
                        content = data['content']
                        
                        if 'parts' in content:
                            for part in content['parts']:
                                # Look for text field in part
                                if 'text' in part:
                                    text_chunk = part['text']
                                    
                                    # Skip if this is a function_call (not final response)
                                    if 'function_call' not in part:
                                        full_response += text_chunk
                                        print(f"✍️  Added text chunk: {text_chunk[:100]}...")
                                        print(f"✍️  Total accumulated: {len(full_response)} chars")
                    
                    # Alternative: direct text field
                    elif 'text' in data:
                        full_response += data['text']
                        print(f"✍️  Added direct text: {len(full_response)} chars")
                        
                except json.JSONDecodeError as e:
                    print(f"⚠️  JSON decode error: {e}")
                    continue
                except Exception as e:
                    print(f"⚠️  Error parsing line: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
        
        if full_response:
            print(f"\n✅ Agent response received ({len(full_response)} chars)")
            print(f"🤖 Full response:\n{full_response}\n")
            return full_response.strip()
        else:
            print("❌ No response text extracted from stream")
            return "I couldn't generate a response. Please try again."
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return "The request timed out. Please try again."
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        if e.response:
            print(f"Status: {e.response.status_code}")
            print(f"Body: {e.response.text[:500]}")
        return f"Error: HTTP {e.response.status_code if e.response else 'Unknown'}"
    except Exception as e:
        print(f"❌ Error querying agent: {e}")
        import traceback
        traceback.print_exc()
        return f"An error occurred: {str(e)}"


@functions_framework.http
def teams_webhook(request):
    """
    Main HTTP Cloud Function handler.
    Routes requests to health check or Teams message processing.
    """
    
    # Health check endpoint - GET request, no JSON needed
    if request.path == '/health' or request.method == 'GET':
        return jsonify({
            "status": "healthy",
            "project": PROJECT_ID,
            "location": LOCATION,
            "resource_id": RESOURCE_ID,
            "base_url": BASE_URL,
            "active_sessions": len(sessions)
        }), 200
    
    # CORS preflight
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, GET',
            'Access-Control-Allow-Headers': 'Content-Type',
        }
        return ('', 204, headers)
    
    # Teams webhook processing - requires JSON
    try:
        activity = request.get_json()
        
        if not activity:
            return jsonify({"error": "No activity data"}), 400
        
        activity_type = activity.get('type')
        conversation_id = activity.get('conversation', {}).get('id', 'default')
        from_user = activity.get('from', {})
        user_name = from_user.get('name', 'User')
        user_id = from_user.get('id', 'teams-user')
        
        print(f"\n{'='*60}")
        print(f"📨 Activity type: {activity_type}")
        print(f"💬 Conversation: {conversation_id}")
        print(f"👤 User: {user_name} ({user_id})")
        
        # Bot added to conversation
        if activity_type == 'conversationUpdate':
            members_added = activity.get('membersAdded', [])
            if members_added:
                session_id = create_session(conversation_id, user_id)
                
                welcome_message = """👋 Hello! I'm your ServiceNow assistant powered by Google Agent Engine.

I can help you with:
• 📋 **Incidents**: Create, list, update, close
• 🛒 **Service Catalog**: Browse and request items
• 🔄 **Change Requests**: Create and manage changes
• 👥 **Users & Groups**: Search and assign
• 🔍 **Problems**: View and track

**Try:**
- "Show me all open incidents"
- "Create an incident for broken laptop"
- "What can I request from catalog?"

Just ask me anything!"""
                
                return jsonify({
                    "type": "message",
                    "text": welcome_message
                }), 200
        
        # Handle user messages
        if activity_type == 'message':
            user_message = activity.get('text', '').strip()
            
            if not user_message:
                return jsonify({"error": "Empty message"}), 400
            
            print(f"💬 Message: {user_message}")
            
            # Get or create session
            session_id = create_session(conversation_id, user_id)
            
            # Query agent
            agent_response = query_agent(session_id, user_message, user_id)
            
            print(f"\n🤖 Sending response to Teams")
            print(f"{'='*60}\n")
            
            # Return to Teams
            return jsonify({
                "type": "message",
                "text": agent_response
            }), 200
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        print(f"❌ Error in webhook: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "type": "message",
            "text": "Sorry, I encountered an error."
        }), 500
