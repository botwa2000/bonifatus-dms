# Multi-Cloud Storage Provider Implementation Plan
## Bonifatus DMS - OneDrive Integration + Scalable Multi-Provider Architecture

**Status**: Implementation Plan - Ready for Execution
**Priority**: High
**Estimated Effort**: 8-10 hours remaining
**Current State**: Backend 80% complete, Frontend 0% complete
**Last Updated**: 2025-12-26

---

## Executive Summary

Transform Bonifatus DMS from Google Drive-only to a multi-cloud platform supporting OneDrive, with architecture ready for Dropbox, Box, and future providers.

### Current Implementation Status

**✅ COMPLETED (Backend Core - 80%)**:
- Base provider abstraction layer (base_provider.py, provider_factory.py)
- Google Drive provider refactored to use new pattern
- OneDrive provider fully implemented using Microsoft Graph API
- DocumentStorageService high-level abstraction
- API endpoints for provider management (/api/v1/storage/providers/*)
- Database migrations created (045, 046)
- OneDrive configuration in config.py
- Router registered in main.py
- User model updated with multi-provider fields

**⚠️ CRITICAL ISSUES IDENTIFIED**:
1. **Document model out of sync** - Still uses `google_drive_file_id` instead of `storage_file_id`
2. **Migrations not applied** - Migrations exist but database schema hasn't been updated
3. **Models.py not reflecting migrations** - Document model needs manual sync

**❌ NOT YET IMPLEMENTED (Frontend - 0%)**:
- Frontend components for multi-cloud UI
- OAuth callback handler for generic providers
- Settings page integration
- Environment variable documentation

---

## Implementation Phases

### Phase 1: Database Schema Synchronization (30 min)

#### Task 1.1: Update Document Model
**File**: `backend/app/database/models.py` (line 257)

**Current**:
```python
google_drive_file_id = Column(String(100), nullable=False, unique=True)
```

**Required**:
```python
storage_file_id = Column(String(100), nullable=False)
storage_provider_type = Column(String(50), nullable=False, index=True)
```

#### Task 1.2: Run Database Migrations
```bash
cd backend
alembic upgrade head
```

**Validation**:
```bash
alembic current  # Should show migration 046 as current
```

---

### Phase 2: Frontend Multi-Provider UI (3-4 hours)

#### Task 2.1: Create Storage Provider Service
**New File**: `frontend/src/services/storage-provider.service.ts`

**Methods**:
```typescript
class StorageProviderService {
  async getAvailableProviders(): Promise<ProviderInfo[]>
  async getAuthorizationUrl(providerType: string): Promise<{ authorization_url: string }>
  async handleOAuthCallback(providerType: string, code: string, state: string): Promise<void>
  async activateProvider(providerType: string): Promise<void>
  async disconnectProvider(providerType: string): Promise<void>
  async getActiveProvider(): Promise<{ active_provider: string | null }>
}
```

**API Endpoints**:
- `GET /api/v1/storage/providers/available`
- `GET /api/v1/storage/providers/{type}/authorize`
- `POST /api/v1/storage/providers/{type}/callback`
- `POST /api/v1/storage/providers/{type}/activate`
- `POST /api/v1/storage/providers/{type}/disconnect`
- `GET /api/v1/storage/active-provider`

#### Task 2.2: Create Provider Card Component
**New File**: `frontend/src/components/settings/ProviderCard.tsx`

**Props**:
```typescript
interface ProviderCardProps {
  provider: {
    type: string          // 'google_drive', 'onedrive'
    name: string          // 'Google Drive', 'OneDrive'
    connected: boolean
    is_active: boolean
    enabled: boolean
  }
  onConnect: (type: string) => void
  onDisconnect: (type: string) => void
  onActivate: (type: string) => void
}
```

**UI Elements**:
- Provider icon
- Connection status badge
- Active provider indicator
- Connect/Disconnect buttons
- Set as Active button

#### Task 2.3: Create Generic OAuth Callback Handler
**New File**: `frontend/src/app/settings/storage/[provider]/callback/page.tsx`

**Pattern**:
```typescript
export default function ProviderCallbackPage() {
  const params = useParams()
  const provider = params.provider as string

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code')
      const state = searchParams.get('state')
      await storageProviderService.handleOAuthCallback(provider, code, state)
      router.push('/settings')
    }
    handleCallback()
  }, [])

  return <LoadingState message={`Connecting ${provider}...`} />
}
```

#### Task 2.4: Update Settings Page
**File**: `frontend/src/app/settings/page.tsx` (lines 663-729)

**Changes**:
1. Remove hardcoded Google Drive UI
2. Add provider state:
```typescript
const [providers, setProviders] = useState<ProviderInfo[]>([])
```

3. Fetch providers on mount:
```typescript
useEffect(() => {
  const data = await storageProviderService.getAvailableProviders()
  setProviders(data.providers)
}, [])
```

4. Render dynamically:
```typescript
{providers.map(provider => (
  <ProviderCard key={provider.type} provider={provider} ... />
))}
```

---

### Phase 3: Environment Configuration (30 min)

#### Task 3.1: Update .env File
**File**: `backend/.env`

**Add**:
```bash
# OneDrive OAuth Configuration
ONEDRIVE_CLIENT_ID=your-azure-app-id
ONEDRIVE_CLIENT_SECRET=your-azure-app-secret
ONEDRIVE_REDIRECT_URI=http://localhost:3000/settings/storage/onedrive/callback
ONEDRIVE_FOLDER_NAME=Bonifatus_DMS_Dev
```

#### Task 3.2: Document Azure App Setup
Add Azure Portal app registration instructions to deployment guide.

---

### Phase 4: Code Updates (1-2 hours)

#### Task 4.1: Update Document Upload Endpoints
**File**: `backend/app/api/documents.py`

**Replace**:
```python
# Old
result = drive_service.upload_document(...)

# New
result = document_storage_service.upload_document(
    user=current_user,
    file_content=file_content,
    filename=filename,
    mime_type=mime_type
)

# Store with provider info
document.storage_file_id = result.file_id
document.storage_provider_type = result.provider_type
```

#### Task 4.2: Update Document Download/Delete
Replace all `drive_service` calls with `document_storage_service`.

---

### Phase 5: Testing (2-3 hours)

#### Task 5.1: Backend API Testing
Test all storage provider endpoints with Postman/curl.

#### Task 5.2: OAuth Flow Testing
**Google Drive**:
1. Click "Connect Google Drive"
2. Authorize on Google
3. Callback to `/settings/storage/google_drive/callback`
4. Tokens stored, status shows "Connected"

**OneDrive** (same flow):
1. Click "Connect OneDrive"
2. Authorize on Microsoft
3. Callback to `/settings/storage/onedrive/callback`
4. Tokens stored, status shows "Connected"

#### Task 5.3: Document Operations Testing
1. Upload with Google Drive active
2. Switch to OneDrive
3. Upload with OneDrive active
4. Verify `storage_provider_type` in database
5. Test download/delete from both

---

## Critical Files Reference

### Backend (Completed ✅)
1. `backend/app/services/storage/base_provider.py`
2. `backend/app/services/storage/provider_factory.py`
3. `backend/app/services/storage/google_drive_provider.py`
4. `backend/app/services/storage/onedrive_provider.py`
5. `backend/app/services/document_storage_service.py`
6. `backend/app/api/storage_providers.py`
7. `backend/app/core/config.py`
8. `backend/alembic/versions/045_add_multi_provider_storage.py`
9. `backend/alembic/versions/046_document_multi_provider.py`

### Backend (Needs Updates ⚠️)
1. `backend/app/database/models.py` - Document model (line 257)
2. `backend/app/api/documents.py` - Use new service
3. `backend/.env` - Add OneDrive config

### Frontend (To Create ❌)
1. `frontend/src/services/storage-provider.service.ts`
2. `frontend/src/components/settings/ProviderCard.tsx`
3. `frontend/src/app/settings/storage/[provider]/callback/page.tsx`

### Frontend (To Update ⚠️)
1. `frontend/src/app/settings/page.tsx` - Multi-provider UI

---

## Environment Variables

### Development
```bash
ONEDRIVE_CLIENT_ID=dev-app-id
ONEDRIVE_CLIENT_SECRET=dev-app-secret
ONEDRIVE_REDIRECT_URI=http://localhost:3000/settings/storage/onedrive/callback
ONEDRIVE_FOLDER_NAME=Bonifatus_DMS_Dev
```

### Production
```bash
ONEDRIVE_CLIENT_ID=prod-app-id
ONEDRIVE_CLIENT_SECRET=prod-app-secret
ONEDRIVE_REDIRECT_URI=https://bonidoc.com/settings/storage/onedrive/callback
ONEDRIVE_FOLDER_NAME=Bonifatus_DMS
```

---

## Azure App Registration Steps

1. Go to https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps
2. Click "New registration"
3. Name: "Bonifatus DMS"
4. Redirect URI: `http://localhost:3000/settings/storage/onedrive/callback`
5. Click "Register"
6. Copy "Application (client) ID" → `ONEDRIVE_CLIENT_ID`
7. Go to "Certificates & secrets" → "New client secret"
8. Copy secret → `ONEDRIVE_CLIENT_SECRET`
9. Go to "API permissions" → Add `Files.ReadWrite.All`, `offline_access`
10. Click "Grant admin consent"

---

## Next Immediate Actions (Priority Order)

1. ✅ **Update Document model** - Change line 257 in models.py
2. ✅ **Run migrations** - `alembic upgrade head`
3. ✅ **Create storage-provider.service.ts** - Frontend API service
4. ✅ **Create ProviderCard.tsx** - UI component
5. ✅ **Create OAuth callback route** - Dynamic route handler
6. ✅ **Update settings page** - Multi-provider UI
7. ✅ **Test OAuth flows** - Both Google Drive and OneDrive
8. ✅ **Update .env** - Add OneDrive configuration

---

## Success Criteria

**Backend**:
- [ ] Migrations applied
- [ ] Document model synced
- [ ] Document API uses new service
- [ ] All provider endpoints work

**Frontend**:
- [ ] Storage service created
- [ ] Provider Card created
- [ ] OAuth callback works
- [ ] Settings page updated
- [ ] Provider icons/branding

**Testing**:
- [ ] Google Drive OAuth works
- [ ] OneDrive OAuth works
- [ ] Upload to both providers works
- [ ] Active provider switching works
- [ ] Disconnect works

**Documentation**:
- [ ] .env updated
- [ ] Azure setup guide added
- [ ] Deployment guide updated

---

**Total Estimated Time**: 8-10 hours of focused development

**Status**: Ready for implementation - all backend infrastructure complete, frontend components are final step.
