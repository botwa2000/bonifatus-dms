# Multi-User Delegate Access - Implementation Plan

**Status:** In Progress - Redesigning invitation flow for better UX and authentication

## Design Overview

### Core Principle
**Invitees MUST have a BoniDoc account (free tier minimum).** All invitation acceptance happens within the authenticated Settings page - no unauthenticated token URLs.

---

## User Flow

### For Owners (Inviters)
**Location:** Settings > Team Access (Pro/Admin users only)

1. Enter email address of person to invite
2. Backend validates email belongs to existing BoniDoc user
3. Send invitation → creates pending record + sends notification email
4. View list of invited delegates with statuses (pending/active/revoked)
5. Can revoke access at any time

### For Delegates (Invitees)
**Two entry points - both require login:**

**Entry Point A: Email Notification**
1. Receive email: "[Owner Name] has invited you to access their documents"
2. Click "View Invitation" → redirects to `/delegates/invitations` or Settings
3. If not logged in → login page → redirects back to invitations
4. If logged in → shows invitation details immediately

**Entry Point B: Settings Page (Primary UX)**
1. Log into BoniDoc normally
2. See notification badge on Settings icon (if pending invitations)
3. See banner: "You have N pending invitations to shared documents"
4. Navigate to **Settings > Shared with Me**
5. View pending invitations list (owner name, email, date)
6. Accept or Decline each invitation
7. View active shared access (documents you can view)

---

## Implementation Checklist

### Phase 1: Backend - User Validation & Authentication ✅ PARTIALLY DONE
- [x] Unique constraint on (owner_user_id, delegate_email)
- [x] Re-invite revoked delegates (update status instead of insert)
- [x] Case-insensitive email lookup
- [ ] **Validate invitee email exists as BoniDoc user before creating invitation**
- [ ] **Add authentication requirement to accept endpoint**
- [ ] **Return user details with pending invitations**

### Phase 2: Backend - Invitation Management API
- [ ] Update `POST /api/v1/delegates/invite`:
  - Add user existence validation
  - Return error if user doesn't exist: "This email is not registered with BoniDoc"
  - Suggest: "Ask them to create a free account first"
- [ ] Update `POST /api/v1/delegates/accept/{token}`:
  - Require authentication (current user must match invited email)
  - Remove token from URL, use request body instead
  - Or deprecate token endpoint entirely
- [ ] Add `GET /api/v1/delegates/pending-invitations`:
  - Return all pending invitations for current authenticated user
  - Include owner details (name, email)
- [ ] Add `POST /api/v1/delegates/respond/{invitation_id}`:
  - Accept or decline invitation
  - Require authentication
  - Validate user email matches invitation

### Phase 3: Frontend - Settings Page Restructure
**Current Structure:**
```
Settings
└── Team Access (Pro users only)
    ├── Invite form
    └── Delegates table
```

**New Structure:**
```
Settings
├── Team Access (Pro/Admin users only)
│   ├── Invite Delegate
│   │   ├── Email input with validation
│   │   └── Error: "User not found" if email doesn't exist
│   └── My Delegates Table
│       └── Columns: Name, Email, Status, Date, Actions
│
└── Shared with Me (All users)
    ├── Pending Invitations
    │   ├── Owner name & email
    │   ├── Role (viewer)
    │   ├── Date invited
    │   └── Accept / Decline buttons
    └── Active Access
        ├── Owner name & email
        ├── Role
        ├── Last accessed
        └── Status badge
```

### Phase 4: Frontend - Notification System
- [ ] Add notification badge to Settings nav item
- [ ] Add banner at top of Settings page when pending invitations exist
- [ ] Count pending invitations on page load
- [ ] Show/hide badge based on count

### Phase 5: Frontend - Components
- [ ] Create `SharedWithMeSection` component
- [ ] Create `PendingInvitationsTable` component
- [ ] Create `ActiveAccessTable` component
- [ ] Update `TeamAccessSection` to show validation errors
- [ ] Add notification badge component

### Phase 6: Email Template Updates
- [ ] Update invitation email template:
  - Clear messaging: "You need a BoniDoc account to accept"
  - Primary CTA: "Log in to BoniDoc" → redirects to Settings
  - Secondary info: "Don't have an account? Create one for free"
  - Remove token from URL (or make it optional)
- [ ] Send reminder emails for pending invitations (optional)

### Phase 7: Acceptance Flow Cleanup
- [ ] Remove `/delegates/accept?token=XXX` page (or make it redirect to Settings)
- [ ] Create `/delegates/invitations` page as alternative entry point
- [ ] Redirect unauthenticated users to login with return URL
- [ ] After login, show invitations in Settings automatically

### Phase 8: Document Access Integration (CRITICAL - Not Yet Implemented)
**This is the most important missing piece - delegates can't actually view documents yet!**

- [ ] Add `acting_as_user_id` parameter to document API endpoints
- [ ] Modify DocumentService to check delegate permissions
- [ ] Fetch documents for delegated owner when acting_as_user_id is set
- [ ] Add user switcher dropdown in navbar (switch between own account and delegated access)
- [ ] Disable upload/edit/delete when viewing as delegate
- [ ] Show banner: "Viewing documents for [Owner Name]"

### Phase 9: Audit & Logging
- [ ] Log all delegate acceptances/declines
- [ ] Log document access by delegates to `delegate_access_logs` table
- [ ] Admin dashboard to view delegate activity

### Phase 10: Testing
- [ ] Test invite validation (existing user vs non-existing)
- [ ] Test invite acceptance flow from Settings
- [ ] Test invite decline flow
- [ ] Test re-inviting revoked users
- [ ] Test notification badge updates
- [ ] Test document access as delegate
- [ ] Test permission boundaries (can't upload/edit/delete)

---

## Current Status

### ✅ Completed
- Database schema (UserDelegate model with unique constraints)
- Basic invite/accept/revoke service methods
- Team Access UI in Settings for owners
- Email invitation sending (via Brevo)
- Re-invite revoked delegates (update instead of insert)
- Case-insensitive email lookup
- Pydantic schema fixes (UUID types)
- Logging verbosity improvements

### 🚧 In Progress
- Redesigning acceptance flow to require authentication
- Adding user validation to invitation process

### ❌ Not Started
- "Shared with Me" section in Settings
- Notification badge system
- Document access integration (CRITICAL)
- User switcher for delegated access
- Audit logging

---

## Technical Notes

### Database Schema (Already Implemented)
```sql
user_delegates
  - id (UUID, PK)
  - owner_user_id (UUID, FK -> users.id)
  - delegate_user_id (UUID, FK -> users.id, nullable)
  - delegate_email (VARCHAR, not null)
  - role (VARCHAR: viewer/editor/owner)
  - status (VARCHAR: pending/active/revoked)
  - invitation_token (VARCHAR, unique)
  - invitation_sent_at (TIMESTAMP)
  - invitation_expires_at (TIMESTAMP)
  - invitation_accepted_at (TIMESTAMP)
  - access_expires_at (TIMESTAMP, nullable)
  - revoked_at (TIMESTAMP, nullable)
  - UNIQUE(owner_user_id, delegate_email)
```

### API Endpoints

**Current:**
- `POST /api/v1/delegates/invite` - Create invitation
- `GET /api/v1/delegates` - List my delegates
- `GET /api/v1/delegates/granted-to-me` - List my active access
- `POST /api/v1/delegates/accept/{token}` - Accept invitation (NEEDS REDESIGN)
- `DELETE /api/v1/delegates/{id}` - Revoke access

**To Add:**
- `GET /api/v1/delegates/pending-invitations` - Get invitations for current user
- `POST /api/v1/delegates/respond/{invitation_id}` - Accept/decline invitation
- `GET /api/v1/documents?acting_as={owner_user_id}` - View delegated documents

---

## Priority Order

1. **HIGH:** Add user validation to invite endpoint (prevent inviting non-existent users)
2. **HIGH:** Add authentication to acceptance flow
3. **HIGH:** Build "Shared with Me" section in Settings
4. **CRITICAL:** Implement document access for delegates (Phase 8)
5. **MEDIUM:** Add notification badges
6. **MEDIUM:** Update email templates
7. **LOW:** Audit logging
8. **LOW:** Admin dashboard

---

## Open Questions

1. Should we keep the email token acceptance as a fallback, or force Settings-only?
   - **Decision:** Settings-only for cleaner UX and security
2. What happens if an invited user doesn't have an account?
   - **Decision:** Show error message, suggest creating free account first
3. Should we auto-accept on first login if pending invitation exists?
   - **Decision:** No - require explicit acceptance for clarity
4. Email verification required before accepting invitations?
   - **Decision:** Not needed - if user can login, email is verified

---

**Last Updated:** 2025-12-20
**Current Sprint:** Phase 1-2 (Backend validation & authentication)
