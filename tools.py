import os
import requests
from requests.auth import HTTPBasicAuth
from google.cloud import secretmanager

def get_secret(secret_name: str) -> str:
    """
    Retrieve secret from Google Secret Manager.
    
    Args:
        secret_name: Name of the secret in Secret Manager
        
    Returns:
        Secret value as string
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
        raise Exception(f"Failed to retrieve secret '{secret_name}': {e}")

# ServiceNow configuration
print("🔐 Loading ServiceNow credentials from Secret Manager...")

SNOW_BASE_URL = "https://...service-now.com/api/now/table"
SNOW_USERNAME = os.getenv("SNOW_USERNAME")
SNOW_PASSWORD = get_secret("ServiceNow_Instance_Password")

print(f"✅ ServiceNow credentials loaded successfully")

# ========== INCIDENT MANAGEMENT ==========

def list_incidents(query: str = "active=true", limit: int = 10) -> dict:
    """
    List ServiceNow incidents.
    
    Args:
        query: Filter query (e.g., "active=true", "priority=1", "assigned_to=username")
        limit: Maximum number of results (default 10)
    
    Returns:
        Dictionary with incident list
    """
    try:
        params = {
            "sysparm_query": query,
            "sysparm_limit": limit,
            "sysparm_display_value": "true"
        }
        
        response = requests.get(
            f"{SNOW_BASE_URL}/incident",
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            params=params,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}

def create_incident(short_description: str, description: str = "", 
                   priority: str = "3", urgency: str = "3",
                   assignment_group: str = "", assigned_to: str = "",
                   category: str = "", subcategory: str = "") -> dict:
    """
    Create a new ServiceNow incident.
    
    Args:
        short_description: Brief title of the incident (required)
        description: Detailed description
        priority: 1=Critical, 2=High, 3=Moderate, 4=Low, 5=Planning
        urgency: 1=High, 2=Medium, 3=Low
        assignment_group: Assignment group name or sys_id
        assigned_to: User name or sys_id to assign
        category: Incident category (e.g., "Hardware", "Software", "Network")
        subcategory: Incident subcategory
    
    Returns:
        Dictionary with created incident details
    """
    try:
        data = {
            "short_description": short_description,
            "description": description,
            "priority": priority,
            "urgency": urgency
        }
        
        if assignment_group:
            data["assignment_group"] = assignment_group
        if assigned_to:
            data["assigned_to"] = assigned_to
        if category:
            data["category"] = category
        if subcategory:
            data["subcategory"] = subcategory
        
        response = requests.post(
            f"{SNOW_BASE_URL}/incident",
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            json=data,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}

def get_incident(sys_id: str) -> dict:
    """
    Get a specific ServiceNow incident by sys_id.
    
    Args:
        sys_id: Unique system ID of the incident
    
    Returns:
        Dictionary with incident details
    """
    try:
        response = requests.get(
            f"{SNOW_BASE_URL}/incident/{sys_id}",
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={"Accept": "application/json"},
            params={"sysparm_display_value": "true"},
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}

def update_incident(sys_id: str, state: str = None, work_notes: str = None,
                   close_notes: str = None, assignment_group: str = None,
                   assigned_to: str = None, **kwargs) -> dict:
    """
    Update a ServiceNow incident.
    
    Args:
        sys_id: Unique system ID of the incident
        state: 1=New, 2=In Progress, 3=On Hold, 6=Resolved, 7=Closed, 8=Canceled
        work_notes: Work notes to add
        close_notes: Closing notes (required when closing)
        assignment_group: Change assignment group
        assigned_to: Change assigned user
        **kwargs: Any other incident fields
    
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
        if assignment_group:
            data["assignment_group"] = assignment_group
        if assigned_to:
            data["assigned_to"] = assigned_to
        data.update(kwargs)
        
        response = requests.patch(
            f"{SNOW_BASE_URL}/incident/{sys_id}",
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            json=data,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}

# ========== SERVICE REQUEST CATALOG ==========

def list_service_requests(query: str = "active=true", limit: int = 10) -> dict:
    """
    List service catalog requests (RITM - Requested Items).
    
    Args:
        query: Filter query (e.g., "active=true", "state=2")
        limit: Maximum number of results
    
    Returns:
        Dictionary with service request list
    """
    try:
        params = {
            "sysparm_query": query,
            "sysparm_limit": limit,
            "sysparm_display_value": "true"
        }
        
        response = requests.get(
            f"{SNOW_BASE_URL}/sc_req_item",
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={"Accept": "application/json"},
            params=params,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}

def create_service_request(catalog_item: str, short_description: str,
                          description: str = "", quantity: int = 1) -> dict:
    """
    Create a new service catalog request.
    
    Args:
        catalog_item: Catalog item sys_id or name
        short_description: Brief description
        description: Detailed description
        quantity: Quantity requested
    
    Returns:
        Dictionary with created request details
    """
    try:
        data = {
            "cat_item": catalog_item,
            "short_description": short_description,
            "description": description,
            "quantity": quantity
        }
        
        response = requests.post(
            f"{SNOW_BASE_URL}/sc_req_item",
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            json=data,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}

def get_service_request(sys_id: str) -> dict:
    """
    Get service request details.
    
    Args:
        sys_id: Service request sys_id
    
    Returns:
        Dictionary with request details
    """
    try:
        response = requests.get(
            f"{SNOW_BASE_URL}/sc_req_item/{sys_id}",
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={"Accept": "application/json"},
            params={"sysparm_display_value": "true"},
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}

# ========== SERVICE CATALOG ITEMS ==========

def list_catalog_items(category: str = "", limit: int = 50) -> dict:
    """
    List available service catalog items that users can request.
    
    Args:
        category: Filter by category name (optional)
        limit: Maximum number of results
    
    Returns:
        Dictionary with catalog items including name, description, and sys_id
    """
    try:
        query = "active=true"
        if category:
            query += f"^categoryLIKE{category}"
        
        params = {
            "sysparm_query": query,
            "sysparm_limit": limit,
            "sysparm_fields": "sys_id,name,short_description,description,category,price,picture",
            "sysparm_display_value": "true"
        }
        
        response = requests.get(
            f"{SNOW_BASE_URL}/sc_cat_item",
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={"Accept": "application/json"},
            params=params,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}

def search_catalog_items(search_term: str, limit: int = 20) -> dict:
    """
    Search for catalog items by name or description.
    
    Args:
        search_term: Search keyword (e.g., "laptop", "software", "access")
        limit: Maximum results
    
    Returns:
        Dictionary with matching catalog items
    """
    try:
        params = {
            "sysparm_query": f"active=true^nameLIKE{search_term}^ORshort_descriptionLIKE{search_term}^ORdescriptionLIKE{search_term}",
            "sysparm_limit": limit,
            "sysparm_fields": "sys_id,name,short_description,category,price",
            "sysparm_display_value": "true"
        }
        
        response = requests.get(
            f"{SNOW_BASE_URL}/sc_cat_item",
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={"Accept": "application/json"},
            params=params,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}

def get_catalog_item_details(sys_id: str) -> dict:
    """
    Get detailed information about a specific catalog item.
    
    Args:
        sys_id: Catalog item sys_id
    
    Returns:
        Dictionary with full catalog item details
    """
    try:
        response = requests.get(
            f"{SNOW_BASE_URL}/sc_cat_item/{sys_id}",
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={"Accept": "application/json"},
            params={"sysparm_display_value": "true"},
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}

def list_catalog_categories(limit: int = 50) -> dict:
    """
    List all service catalog categories.
    
    Args:
        limit: Maximum results
    
    Returns:
        Dictionary with catalog categories
    """
    try:
        params = {
            "sysparm_query": "active=true",
            "sysparm_limit": limit,
            "sysparm_fields": "sys_id,title,description,parent",
            "sysparm_display_value": "true"
        }
        
        response = requests.get(
            f"{SNOW_BASE_URL}/sc_category",
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={"Accept": "application/json"},
            params=params,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}

# ========== REFERENCE DATA / SUGGESTIONS ==========

def get_incident_categories(limit: int = 50) -> dict:
    """
    Get list of available incident categories for suggestions.
    
    Returns:
        Dictionary with category choices
    """
    try:
        params = {
            "sysparm_query": "name=incident^element=category",
            "sysparm_limit": 1
        }
        
        response = requests.get(
            f"{SNOW_BASE_URL}/sys_choice",
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={"Accept": "application/json"},
            params=params,
            timeout=30
        )
        
        response.raise_for_status()
        data = response.json()
        
        # Get all category choices
        if data.get("result"):
            params = {
                "sysparm_query": "name=incident^element=category^inactive=false",
                "sysparm_limit": limit,
                "sysparm_fields": "label,value"
            }
            
            response = requests.get(
                f"{SNOW_BASE_URL}/sys_choice",
                auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
                headers={"Accept": "application/json"},
                params=params,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
        
        return {"result": []}
        
    except Exception as e:
        return {"error": str(e)}

def get_priority_urgency_info() -> dict:
    """
    Get information about priority and urgency levels.
    
    Returns:
        Dictionary with priority/urgency guidelines
    """
    return {
        "priority": {
            "1": "Critical - System down, multiple users affected",
            "2": "High - Major functionality impaired",
            "3": "Moderate - Some functionality affected",
            "4": "Low - Minor issue, workaround available",
            "5": "Planning - Enhancement or future need"
        },
        "urgency": {
            "1": "High - Immediate attention required",
            "2": "Medium - Attention needed soon",
            "3": "Low - Can wait, not time-sensitive"
        },
        "impact": {
            "1": "High - Affects many users or critical business",
            "2": "Medium - Affects some users or important business",
            "3": "Low - Affects few users or minor business impact"
        }
    }

def get_change_types_info() -> dict:
    """
    Get information about change request types.
    
    Returns:
        Dictionary with change type descriptions
    """
    return {
        "types": {
            "standard": "Pre-approved, low-risk changes following established procedures",
            "normal": "Requires full change approval process and CAB review",
            "emergency": "Urgent changes needed to resolve critical incidents"
        },
        "risk_levels": {
            "low": "Minimal impact, easy rollback, tested procedure",
            "moderate": "Some impact possible, rollback available",
            "high": "Significant impact potential, complex rollback"
        }
    }

def get_my_info() -> dict:
    """
    Get current user's information from ServiceNow.
    
    Returns:
        Dictionary with user details
    """
    try:
        # Get current user (the one authenticated)
        params = {
            "sysparm_query": f"user_name={SNOW_USERNAME}",
            "sysparm_limit": 1,
            "sysparm_fields": "sys_id,name,email,user_name,title,department,manager,phone"
        }
        
        response = requests.get(
            f"{SNOW_BASE_URL}/sys_user",
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={"Accept": "application/json"},
            params=params,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}


# ========== CHANGE REQUEST MANAGEMENT ==========

def list_change_requests(query: str = "active=true", limit: int = 10) -> dict:
    """
    List change requests.
    
    Args:
        query: Filter query (e.g., "state=1", "type=normal")
        limit: Maximum number of results
    
    Returns:
        Dictionary with change request list
    """
    try:
        params = {
            "sysparm_query": query,
            "sysparm_limit": limit,
            "sysparm_display_value": "true"
        }
        
        response = requests.get(
            f"{SNOW_BASE_URL}/change_request",
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={"Accept": "application/json"},
            params=params,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}

def create_change_request(short_description: str, description: str = "",
                         type: str = "normal", risk: str = "moderate",
                         priority: str = "3", assignment_group: str = "",
                         start_date: str = "", end_date: str = "") -> dict:
    """
    Create a new change request.
    
    Args:
        short_description: Brief title (required)
        description: Detailed description
        type: standard, normal, emergency
        risk: low, moderate, high
        priority: 1=Critical, 2=High, 3=Moderate, 4=Low
        assignment_group: Assignment group
        start_date: Planned start date (format: YYYY-MM-DD HH:MM:SS)
        end_date: Planned end date
    
    Returns:
        Dictionary with created change request
    """
    try:
        data = {
            "short_description": short_description,
            "description": description,
            "type": type,
            "risk": risk,
            "priority": priority
        }
        
        if assignment_group:
            data["assignment_group"] = assignment_group
        if start_date:
            data["start_date"] = start_date
        if end_date:
            data["end_date"] = end_date
        
        response = requests.post(
            f"{SNOW_BASE_URL}/change_request",
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            json=data,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}

def get_change_request(sys_id: str) -> dict:
    """
    Get change request details.
    
    Args:
        sys_id: Change request sys_id
    
    Returns:
        Dictionary with change request details
    """
    try:
        response = requests.get(
            f"{SNOW_BASE_URL}/change_request/{sys_id}",
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={"Accept": "application/json"},
            params={"sysparm_display_value": "true"},
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}

def update_change_request(sys_id: str, state: str = None, work_notes: str = None,
                         close_notes: str = None, **kwargs) -> dict:
    """
    Update a change request.
    
    Args:
        sys_id: Change request sys_id
        state: -5=New, -4=Assess, -3=Authorize, -2=Scheduled, -1=Implement, 0=Review, 3=Closed
        work_notes: Work notes to add
        close_notes: Close notes
        **kwargs: Other fields to update
    
    Returns:
        Dictionary with updated change request
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
        
        response = requests.patch(
            f"{SNOW_BASE_URL}/change_request/{sys_id}",
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            json=data,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}

# ========== ASSIGNMENT GROUPS ==========

def list_assignment_groups(query: str = "active=true", limit: int = 50) -> dict:
    """
    List assignment groups.
    
    Args:
        query: Filter query (e.g., "active=true", "name=IT Support")
        limit: Maximum number of results
    
    Returns:
        Dictionary with assignment group list
    """
    try:
        params = {
            "sysparm_query": query,
            "sysparm_limit": limit,
            "sysparm_fields": "sys_id,name,description,manager,type"
        }
        
        response = requests.get(
            f"{SNOW_BASE_URL}/sys_user_group",
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={"Accept": "application/json"},
            params=params,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}

def get_assignment_group(group_name: str) -> dict:
    """
    Get assignment group details by name.
    
    Args:
        group_name: Assignment group name
    
    Returns:
        Dictionary with group details including sys_id
    """
    try:
        params = {
            "sysparm_query": f"name={group_name}",
            "sysparm_limit": 1
        }
        
        response = requests.get(
            f"{SNOW_BASE_URL}/sys_user_group",
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={"Accept": "application/json"},
            params=params,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}

# ========== USER MANAGEMENT ==========

def search_users(query: str, limit: int = 10) -> dict:
    """
    Search for users by name, email, or username.
    
    Args:
        query: Search query (name, email, or user_name)
        limit: Maximum results
    
    Returns:
        Dictionary with user list
    """
    try:
        params = {
            "sysparm_query": f"nameLIKE{query}^ORemailLIKE{query}^ORuser_nameLIKE{query}^active=true",
            "sysparm_limit": limit,
            "sysparm_fields": "sys_id,name,email,user_name,title,department"
        }
        
        response = requests.get(
            f"{SNOW_BASE_URL}/sys_user",
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={"Accept": "application/json"},
            params=params,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}

# ========== PROBLEM MANAGEMENT ==========

def list_problems(query: str = "active=true", limit: int = 10) -> dict:
    """
    List problems.
    
    Args:
        query: Filter query
        limit: Maximum results
    
    Returns:
        Dictionary with problem list
    """
    try:
        params = {
            "sysparm_query": query,
            "sysparm_limit": limit,
            "sysparm_display_value": "true"
        }
        
        response = requests.get(
            f"{SNOW_BASE_URL}/problem",
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={"Accept": "application/json"},
            params=params,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}

def get_problem(sys_id: str) -> dict:
    """
    Get problem details.
    
    Args:
        sys_id: Problem sys_id
    
    Returns:
        Dictionary with problem details
    """
    try:
        response = requests.get(
            f"{SNOW_BASE_URL}/problem/{sys_id}",
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            headers={"Accept": "application/json"},
            params={"sysparm_display_value": "true"},
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}

# Export all tools
# Export all tools
snow_tools = [
    # Incidents
    list_incidents,
    create_incident,
    get_incident,
    update_incident,
    # Service Requests
    list_service_requests,
    create_service_request,
    get_service_request,
    # Service Catalog
    list_catalog_items,
    search_catalog_items,
    get_catalog_item_details,
    list_catalog_categories,
    # Change Requests
    list_change_requests,
    create_change_request,
    get_change_request,
    update_change_request,
    # Assignment Groups
    list_assignment_groups,
    get_assignment_group,
    # Users
    search_users,
    get_my_info,
    # Problems
    list_problems,
    get_problem,
    # Reference Data / Suggestions
    get_incident_categories,
    get_priority_urgency_info,
    get_change_types_info
]

