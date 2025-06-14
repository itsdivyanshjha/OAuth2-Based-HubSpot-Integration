# HubSpot OAuth Integration

## Overview
This project implements a complete HubSpot OAuth integration that allows users to securely connect their HubSpot account and retrieve CRM data (contacts, companies, deals). Features a full-stack implementation with React frontend and Python FastAPI backend.

## Implementation Details

### OAuth 2.0 Authentication
- **Backend (Python/FastAPI)**:
  - `authorize_hubspot()` - Initiates OAuth flow with state validation
  - `oauth2callback_hubspot()` - Handles OAuth callback and token exchange
  - `get_hubspot_credentials()` - Securely retrieves stored credentials
  
- **Frontend (React)**:
  - React component with connection UI and status management
  - OAuth popup window handling with automatic closure detection
  - Integration with existing authentication framework

### CRM Data Retrieval
- **Backend**:
  - `get_items_hubspot()` - Fetches HubSpot CRM data via REST API
  - Data standardization using custom `IntegrationItem` format
  - Retrieves contacts, companies, and deals with proper error handling

- **Frontend**:
  - Dynamic data loading with user-friendly interface
  - Real-time display of retrieved CRM items

## Technologies Used
- **Backend**: Python, FastAPI, Redis, httpx, requests
- **Frontend**: React, Material-UI, Axios
- **OAuth 2.0**: HubSpot OAuth implementation
- **Database**: Redis for temporary credential storage

## Setup Instructions

### Prerequisites
- Python 3.9+
- Node.js
- Redis server
- HubSpot Developer Account

### HubSpot App Configuration
1. Create app at https://developers.hubspot.com/
2. Set redirect URL: `http://localhost:8000/integrations/hubspot/oauth2callback`
3. Configure scopes: `oauth`, `crm.objects.contacts.read`, `crm.objects.companies.read`, `crm.objects.deals.read`
4. Update `CLIENT_ID` and `CLIENT_SECRET` in `backend/integrations/hubspot.py`

### Running the Application

1. **Start Redis**:
   ```bash
   redis-server
   ```

2. **Start Backend**:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

3. **Start Frontend**:
   ```bash
   cd frontend
   npm install
   npm start
   ```

4. **Access Application**: http://localhost:3000

## Usage
1. Select "HubSpot" from integration dropdown
2. Click "Connect to HubSpot"
3. Complete OAuth authorization
4. Click "Load Data" to fetch HubSpot items

## Sample Output
```
contact: Brian Halligan (Sample Contact) (ID: 144032404156)
contact: Maria Johnson (Sample Contact) (ID: 144047940331)
company: HubSpot (ID: 93339835085)
```

## Files Modified/Created
```
backend/integrations/hubspot.py    # Complete HubSpot integration implementation
frontend/src/integrations/hubspot.js  # React component for HubSpot connection
frontend/src/integration-form.js   # Modified to include HubSpot option
frontend/src/data-form.js          # Modified to support HubSpot data loading
README.md                          # Project documentation
```

## Features Implemented
- ✅ Complete OAuth 2.0 flow with security validation
- ✅ HubSpot CRM data retrieval (contacts, companies, deals)
- ✅ Standardized data format conversion
- ✅ React UI integration
- ✅ Error handling and logging
- ✅ Temporary credential storage with Redis

## Key Features Demonstrated
- **Full-Stack Development**: Complete integration from frontend UI to backend API
- **OAuth 2.0 Implementation**: Secure authentication flow with state validation
- **API Integration**: Real-time data fetching from HubSpot's REST API
- **Data Transformation**: Standardized data formatting and error handling
- **Modern Tech Stack**: React, FastAPI, Redis, and Material-UI