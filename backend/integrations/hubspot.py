# hubspot.py

import json
import secrets
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
import asyncio
import requests
from integrations.integration_item import IntegrationItem
from datetime import datetime

from redis_client import add_key_value_redis, get_value_redis, delete_key_redis

# HubSpot app credentials
CLIENT_ID = '740ce6a4-681d-48ba-b289-d85b6fdb9bd8'
CLIENT_SECRET = '2b60222b-a7da-46f4-afdc-c18c840f6a99'

REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'
# Match exactly what HubSpot expects based on your app configuration
REQUIRED_SCOPES = 'oauth%20crm.objects.companies.read%20crm.objects.deals.read%20crm.objects.contacts.read'
OPTIONAL_SCOPES = 'crm.schemas.companies.write%20crm.objects.contacts.write%20crm.schemas.contacts.write%20crm.schemas.deals.read%20crm.schemas.deals.write%20crm.dealsplits.read_write%20crm.objects.companies.write%20crm.schemas.contacts.read%20crm.objects.deals.write%20crm.schemas.companies.read'
authorization_url = f'https://app-na2.hubspot.com/oauth/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={REQUIRED_SCOPES}&optional_scope={OPTIONAL_SCOPES}'

async def authorize_hubspot(user_id, org_id):
    """Start the HubSpot OAuth authorization process"""
    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }
    encoded_state = json.dumps(state_data)
    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', encoded_state, expire=600)

    return f'{authorization_url}&state={encoded_state}'

async def oauth2callback_hubspot(request: Request):
    """Handle HubSpot OAuth callback and exchange code for access token"""
    if request.query_params.get('error'):
        raise HTTPException(status_code=400, detail=request.query_params.get('error'))
    
    code = request.query_params.get('code')
    encoded_state = request.query_params.get('state')
    
    if not code or not encoded_state:
        raise HTTPException(status_code=400, detail='Missing authorization code or state')
    
    state_data = json.loads(encoded_state)
    original_state = state_data.get('state')
    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')

    # Verify state to prevent CSRF attacks
    saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')
    if not saved_state or original_state != json.loads(saved_state).get('state'):
        raise HTTPException(status_code=400, detail='State does not match.')

    # Exchange authorization code for access token
    async with httpx.AsyncClient() as client:
        response, _ = await asyncio.gather(
            client.post(
                'https://api.hubapi.com/oauth/v1/token',
                data={
                    'grant_type': 'authorization_code',
                    'client_id': CLIENT_ID,
                    'client_secret': CLIENT_SECRET,
                    'redirect_uri': REDIRECT_URI,
                    'code': code
                },
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                }
            ),
            delete_key_redis(f'hubspot_state:{org_id}:{user_id}'),
        )

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail='Failed to exchange code for token')

    # Store credentials temporarily in Redis
    await add_key_value_redis(f'hubspot_credentials:{org_id}:{user_id}', json.dumps(response.json()), expire=600)
    
    # Close the OAuth popup window
    close_window_script = """
    <html>
        <script>
            window.close();
        </script>
    </html>
    """
    return HTMLResponse(content=close_window_script)

async def get_hubspot_credentials(user_id, org_id):
    """Retrieve stored HubSpot credentials"""
    credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')
    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found.')
    
    credentials = json.loads(credentials)
    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found.')
    
    # Clean up - delete credentials after retrieval
    await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')
    
    return credentials

def create_integration_item_metadata_object(response_json: dict, item_type: str) -> IntegrationItem:
    """Convert HubSpot API response to IntegrationItem format"""
    
    # Extract common fields that exist across different HubSpot objects
    properties = response_json.get('properties', {})
    
    # Determine name based on object type
    name = None
    if item_type == 'contact':
        first_name = properties.get('firstname', '')
        last_name = properties.get('lastname', '')
        name = f"{first_name} {last_name}".strip() or properties.get('email', 'Unknown Contact')
    elif item_type == 'company':
        name = properties.get('name', 'Unknown Company')
    elif item_type == 'deal':
        name = properties.get('dealname', 'Unknown Deal')
    
    # Convert timestamps
    created_at = properties.get('createdate')
    modified_at = properties.get('lastmodifieddate')
    
    creation_time = None
    last_modified_time = None
    
    if created_at:
        try:
            creation_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except:
            pass
    
    if modified_at:
        try:
            last_modified_time = datetime.fromisoformat(modified_at.replace('Z', '+00:00'))
        except:
            pass

    integration_item = IntegrationItem(
        id=response_json.get('id'),
        type=item_type,
        name=name,
        creation_time=creation_time,
        last_modified_time=last_modified_time,
        url=f"https://app.hubspot.com/{item_type}/{response_json.get('id')}",
    )

    return integration_item

async def get_items_hubspot(credentials):
    """Fetch HubSpot data and return list of IntegrationItem objects"""
    credentials_dict = json.loads(credentials) if isinstance(credentials, str) else credentials
    access_token = credentials_dict.get('access_token')
    
    if not access_token:
        raise HTTPException(status_code=400, detail='No access token found in credentials')

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    integration_items = []

    try:
        # Fetch contacts
        contacts_response = requests.get(
            'https://api.hubapi.com/crm/v3/objects/contacts',
            headers=headers,
            params={'limit': 10}  # Limit for testing
        )
        
        if contacts_response.status_code == 200:
            contacts_data = contacts_response.json()
            for contact in contacts_data.get('results', []):
                integration_items.append(
                    create_integration_item_metadata_object(contact, 'contact')
                )

        # Fetch companies
        companies_response = requests.get(
            'https://api.hubapi.com/crm/v3/objects/companies',
            headers=headers,
            params={'limit': 10}  # Limit for testing
        )
        
        if companies_response.status_code == 200:
            companies_data = companies_response.json()
            for company in companies_data.get('results', []):
                integration_items.append(
                    create_integration_item_metadata_object(company, 'company')
                )

        # Fetch deals
        deals_response = requests.get(
            'https://api.hubapi.com/crm/v3/objects/deals',
            headers=headers,
            params={'limit': 10}  # Limit for testing
        )
        
        if deals_response.status_code == 200:
            deals_data = deals_response.json()
            for deal in deals_data.get('results', []):
                integration_items.append(
                    create_integration_item_metadata_object(deal, 'deal')
                )

        print(f"Retrieved {len(integration_items)} HubSpot items:")
        for item in integration_items:
            print(f"- {item.type}: {item.name} (ID: {item.id})")
        
        # Return formatted string for frontend display
        if integration_items:
            formatted_items = []
            for item in integration_items:
                formatted_items.append(f"{item.type}: {item.name} (ID: {item.id})")
            return "\n".join(formatted_items)
        else:
            return "No HubSpot items found"

    except requests.exceptions.RequestException as e:
        print(f"Error fetching HubSpot data: {e}")
        raise HTTPException(status_code=500, detail=f'Error fetching HubSpot data: {str(e)}')