import os
import requests
from requests.auth import HTTPBasicAuth
from google.cloud import secretmanager

def get_secret(secret_name: str) -> str:
    """
    Retrieve secret from Google Secret Manager.
    No fallback - fails if secret cannot be retrieved.
    
    Args:
        secret_name: Name of the secret in Secret Manager
        
    Returns:
        Secret value as string
        
    Raises:
        Exception if secret cannot be retrieved
    """
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable must be set")
    
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
    
    try:
        response = client.access_secret_version(request={"name": name})
        secret_value = response.payload.data.decode("UTF-8")
        print(f"✅ Successfully retrieved secret: {secret_name}")
        return secret_value
    except Exception as e:
        raise Exception(f"Failed to retrieve secret '{secret_name}' from Secret Manager: {e}")

# ServiceNow configuration - All credentials from Secret Manager
print("🔐 Loading ServiceNow credentials from Secret Manager...")

SNOW_BASE_URL = "https://dev185966.service-now.com/api/now/table/incident"

# Get username from Secret Manager
SNOW_USERNAME = os.getenv("SNOW_USERNAME")

# Get password from Secret Manager
SNOW_PASSWORD = get_secret("ServiceNow_Instance_Password")

print(f"✅ ServiceNow Username: {SNOW_USERNAME}")
print(f"✅ Password loaded (length: {len(SNOW_PASSWORD)} characters)")

# Tool functions
def list_incidents(query: str = "active=true", limit: int = 10) -> dict:
    """
    List ServiceNow incidents.
    
    Args:
        query: Filter query (e.g., "active=true", "priority=1")
        limit: Maximum number of results (default 10)
    
    Returns:
        Dictionary with incident list
    """
    try:
        params = {
            "sysparm_query": query,
            "sysparm_limit": limit
        }
        
        response = requests.get(
            SNOW_BASE_URL,
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            params=params,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.HTTPError as e:
        return {
            "error": f"HTTP {e.response.status_code}",
            "message": e.response.text
        }
    except Exception as e:
        return {"error": str(e)}

def create_incident(short_description: str, description: str = "", 
                   priority: str = "3", urgency: str = "3") -> dict:
    """
    Create a new ServiceNow incident.
    
    Args:
        short_description: Brief title of the incident (required)
        description: Detailed description (optional)
        priority: Priority level 1-5 (1=Critical, 3=Moderate, 5=Planning)
        urgency: Urgency level 1-3 (1=High, 2=Medium, 3=Low)
    
    Returns:
        Dictionary with created incident details including sys_id and number
    """
    try:
        data = {
            "short_description": short_description,
            "description": description,
            "priority": priority,
            "urgency": urgency
        }
        
        response = requests.post(
            SNOW_BASE_URL,
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            json=data,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.HTTPError as e:
        return {
            "error": f"HTTP {e.response.status_code}",
            "message": e.response.text
        }
    except Exception as e:
        return {"error": str(e)}

def get_incident(sys_id: str) -> dict:
    """
    Get a specific ServiceNow incident by sys_id.
    
    Args:
        sys_id: Unique system ID of the incident (36-character UUID)
    
    Returns:
        Dictionary with incident details
    """
    try:
        url = f"{SNOW_BASE_URL}/{sys_id}"
        
        response = requests.get(
            url,
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.HTTPError as e:
        return {
            "error": f"HTTP {e.response.status_code}",
            "message": e.response.text
        }
    except Exception as e:
        return {"error": str(e)}

def update_incident(sys_id: str, state: str = None, work_notes: str = None, 
                   close_notes: str = None, **kwargs) -> dict:
    """
    Update a ServiceNow incident.
    
    Args:
        sys_id: Unique system ID of the incident
        state: New state (7=Closed, 6=Resolved, 2=In Progress, 3=On Hold)
        work_notes: Work notes to add to the incident
        close_notes: Closing notes (required when closing an incident)
        **kwargs: Any other ServiceNow incident fields to update
    
    Returns:
        Dictionary with updated incident details
    """
    try:
        data = {}
        if state:
            data["state"] = state
        if work_notes:
            data["work_notes"] = work_notes
        if close_notes:
            data["close_notes"] = close_notes
        data.update(kwargs)
        
        url = f"{SNOW_BASE_URL}/{sys_id}"
        
        response = requests.patch(
            url,
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            json=data,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.HTTPError as e:
        return {
            "error": f"HTTP {e.response.status_code}",
            "message": e.response.text
        }
    except Exception as e:
        return {"error": str(e)}

# Export all tools
snow_tools = [list_incidents, create_incident, get_incident, update_incident]
