# TODO - Multi-User Document Access Feature

## Concept
Professional tier users can grant **read-only** access to their documents (stored on their Google Drive) to other registered users (Free/Starter/Pro). Delegates can search and view documents but cannot modify, upload, or delete.

## Core Requirements
- ✅ Access to Pro user's cloud storage (Google Drive documents)
- ✅ Delegates can be any tier (Free/Starter/Pro)
- ✅ Read-only access (view & search documents)
- ✅ Simple but secure invitation/acceptance flow
- ✅ No limit on number of delegates
- ✅ Infrastructure ready for future roles (viewer/editor/owner)
- ✅ Only "viewer" role implemented for now

## Implementation Tasks

### Phase 1: Database & Models
- [ ] 1.1 Design `user_delegates` table schema
- [ ] 1.2 Create Alembic migration
- [ ] 1.3 Add SQLAlchemy `UserDelegate` model
- [ ] 1.4 Create Pydantic schemas (DelegateCreate, DelegateResponse, DelegateInvite)
- [ ] 1.5 Add indexes for performance

### Phase 2: Backend - Delegate Management Service
- [ ] 2.1 Create `DelegateService` class
- [ ] 2.2 Implement `invite_delegate(owner_id, email, role='viewer')` - Generate token, send email
- [ ] 2.3 Implement `accept_invitation(token)` - Validate token, create delegate record
- [ ] 2.4 Implement `list_delegates(owner_id)` - Get all delegates for owner
- [ ] 2.5 Implement `list_granted_access(delegate_id)` - Get owners who granted access to delegate
- [ ] 2.6 Implement `revoke_access(owner_id, delegate_id)` - Remove access
- [ ] 2.7 Implement `check_access(delegate_id, owner_id)` - Verify delegate has access

### Phase 3: Backend - API Endpoints
- [ ] 3.1 `POST /api/v1/delegates/invite` - Invite delegate (Pro user only)
- [ ] 3.2 `GET /api/v1/delegates` - List my delegates (as owner)
- [ ] 3.3 `GET /api/v1/delegates/granted-to-me` - List owners who granted me access (as delegate)
- [ ] 3.4 `POST /api/v1/delegates/accept/{token}` - Accept invitation
- [ ] 3.5 `DELETE /api/v1/delegates/{delegate_id}` - Revoke access
- [ ] 3.6 Add tier validation (Pro only for inviting)

### Phase 4: Backend - Document Permissions
- [ ] 4.1 Modify `DocumentService.list_documents()` - Include documents from owners who granted access
- [ ] 4.2 Modify `DocumentService.get_document()` - Allow access if delegate has permission
- [ ] 4.3 Add `acting_as_user_id` parameter to document queries
- [ ] 4.4 Prevent delegates from uploading/editing/deleting documents
- [ ] 4.5 Add audit logging for delegate document access

### Phase 5: Frontend - Delegate Management UI
- [ ] 5.1 Add "Delegates" section to Settings or Profile page
- [ ] 5.2 Build "Invite Delegate" form (email input, Pro tier check)
- [ ] 5.3 Build delegates list table (email, status, invited date, actions)
- [ ] 5.4 Add "Revoke Access" button with confirmation
- [ ] 5.5 Build "My Access" view showing owners who granted access

### Phase 6: Frontend - Context Switching
- [ ] 6.1 Add account switcher dropdown in header (if user has granted access)
- [ ] 6.2 Store selected account context in React state
- [ ] 6.3 Pass `acting_as_user_id` to document API calls
- [ ] 6.4 Show visual indicator when viewing as delegate (badge/banner)
- [ ] 6.5 Disable upload/edit/delete buttons when in delegate mode

### Phase 7: Invitation Flow & Notifications
- [ ] 7.1 Create email template for delegate invitation
- [ ] 7.2 Generate secure random invitation token (expires in 7 days)
- [ ] 7.3 Send invitation email with acceptance link
- [ ] 7.4 Build invitation acceptance page (`/delegates/accept?token=xxx`)
- [ ] 7.5 Handle token validation and expiry
- [ ] 7.6 Send confirmation emails to both parties on acceptance
- [ ] 7.7 Send notification when owner revokes access
- [ ] 7.8 Send notification when access expires (if time-limited)

### Phase 8: Access Management
- [ ] 8.1 Implement revoke access functionality (owner can remove delegate anytime)
- [ ] 8.2 Add `revoked_at` and `revoked_by` fields tracking
- [ ] 8.3 Implement access expiry (optional time-limited access)
- [ ] 8.4 Add `access_expires_at` field to user_delegates table
- [ ] 8.5 Create background job to automatically revoke expired access
- [ ] 8.6 Add "Extend Access" functionality for owner
- [ ] 8.7 Show access expiry warning to delegates (7 days before expiry)

### Phase 9: Audit & Security
- [ ] 9.1 Add `delegate_access_logs` table for audit trail
- [ ] 9.2 Log every document view by delegate (document_id, delegate_id, timestamp)
- [ ] 9.3 Add "Activity Log" view for owner to see delegate activity
- [ ] 9.4 Implement rate limiting on document access
- [ ] 9.5 Add security checks to prevent privilege escalation

### Phase 10: Testing
- [ ] 10.1 Test invitation flow end-to-end
- [ ] 10.2 Test document access permissions (delegate can view, cannot edit)
- [ ] 10.3 Test context switching between own account and delegated accounts
- [ ] 10.4 Test revoke access
- [ ] 10.5 Test access expiry and automatic revocation
- [ ] 10.6 Test notifications (invite, accept, revoke, expiry)
- [ ] 10.7 Test with multiple delegates and multiple owners
- [ ] 10.8 Test tier restrictions (only Pro can invite)
- [ ] 10.9 Test audit logs and activity tracking

## Database Schema

### `user_delegates` Table
```sql
CREATE TABLE user_delegates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    delegate_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    delegate_email VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'viewer' CHECK (role IN ('viewer', 'editor', 'owner')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'revoked')),

    -- Invitation management
    invitation_token VARCHAR(100) UNIQUE,
    invitation_sent_at TIMESTAMP WITH TIME ZONE,
    invitation_expires_at TIMESTAMP WITH TIME ZONE,
    invitation_accepted_at TIMESTAMP WITH TIME ZONE,

    -- Access management
    access_expires_at TIMESTAMP WITH TIME ZONE,  -- Optional time-limited access
    last_accessed_at TIMESTAMP WITH TIME ZONE,    -- Track last activity

    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    revoked_at TIMESTAMP WITH TIME ZONE,
    revoked_by UUID REFERENCES users(id),

    UNIQUE(owner_user_id, delegate_email),
    CHECK (owner_user_id != delegate_user_id)
);

CREATE INDEX idx_delegates_owner ON user_delegates(owner_user_id);
CREATE INDEX idx_delegates_delegate_user ON user_delegates(delegate_user_id);
CREATE INDEX idx_delegates_delegate_email ON user_delegates(delegate_email);
CREATE INDEX idx_delegates_status ON user_delegates(status);
CREATE INDEX idx_delegates_invitation_token ON user_delegates(invitation_token);
CREATE INDEX idx_delegates_access_expires ON user_delegates(access_expires_at) WHERE access_expires_at IS NOT NULL;
```

### `delegate_access_logs` Table (Audit)
```sql
CREATE TABLE delegate_access_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    delegate_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    action VARCHAR(20) NOT NULL CHECK (action IN ('view', 'download', 'search')),
    accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ip_address VARCHAR(45),
    user_agent TEXT
);

CREATE INDEX idx_access_logs_delegate ON delegate_access_logs(delegate_user_id, accessed_at);
CREATE INDEX idx_access_logs_owner ON delegate_access_logs(owner_user_id, accessed_at);
CREATE INDEX idx_access_logs_document ON delegate_access_logs(document_id);
```

## Permission Matrix (Current Implementation)

| Role    | View | Search | Download | Upload | Edit | Delete |
|---------|------|--------|----------|--------|------|--------|
| viewer  | ✅   | ✅     | ✅       | ❌     | ❌   | ❌     |
| editor  | 🔜   | 🔜     | 🔜       | 🔜     | 🔜   | ❌     |
| owner   | 🔜   | 🔜     | 🔜       | 🔜     | 🔜   | 🔜     |

## Status Flow
1. **pending** - Invitation sent, waiting for acceptance
2. **active** - Invitation accepted, delegate has access
3. **revoked** - Access removed by owner

## API Examples

### Invite Delegate
```http
POST /api/v1/delegates/invite
Authorization: Bearer <token>
Content-Type: application/json

{
  "email": "assistant@example.com",
  "role": "viewer"
}

Response 201:
{
  "id": "uuid",
  "delegate_email": "assistant@example.com",
  "status": "pending",
  "invitation_expires_at": "2025-12-22T12:00:00Z"
}
```

### Accept Invitation
```http
POST /api/v1/delegates/accept/abc123token
Authorization: Bearer <token>

Response 200:
{
  "success": true,
  "owner_name": "John Doe",
  "role": "viewer"
}
```

### List Documents (as delegate)
```http
GET /api/v1/documents?acting_as=<owner_user_id>
Authorization: Bearer <token>

Response 200:
{
  "documents": [...],
  "viewing_as_delegate": true,
  "owner_name": "John Doe",
  "permissions": {"can_view": true, "can_upload": false}
}
```

## Notes
- Delegates must be registered users (Free/Starter/Pro tier)
- Only Pro tier users can invite delegates
- No limit on number of delegates (for now)
- Delegates have read-only access to ALL owner's documents
- Future: Allow selective document sharing (specific categories/documents)
- Future: Implement editor and owner roles
- Future: Add time-limited access (expiry dates)
