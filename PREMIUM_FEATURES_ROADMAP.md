# Bonifatus DMS - Premium Features Roadmap

**Version:** 1.0
**Last Updated:** December 2025
**Focus:** Efficiency | Security | Resources | UX

---

## Overview

This document outlines implementation milestones for Premium (Pro) tier features. Each feature is designed with minimal resource overhead, maximum security, and optimal user experience.

---

## Feature 1: Multi-Provider Authentication

**Current State:** Google OAuth only
**Target State:** Email/Password, Google, Facebook, Microsoft, Apple

### Objectives

#### Phase 1: Email/Password Authentication (Priority: HIGH)
- **Goal:** Allow users to register/login with email without OAuth dependencies
- **Security:**
  - Implement bcrypt password hashing (12+ rounds)
  - Email verification with time-limited tokens (1 hour expiry)
  - Password reset flow with secure tokens
  - Rate limiting: 5 failed attempts = 15-minute lockout
  - CAPTCHA integration (hCaptcha - free tier) after 3 failed attempts
- **UX:**
  - "Sign up with Email" button on homepage
  - Password strength indicator (real-time feedback)
  - "Magic link" option (passwordless login via email)
  - Remember device (30-day secure cookie)
- **Resources:**
  - Email sending: Use existing SMTP infrastructure (free)
  - Storage: +minimal (password hashes in existing users table)
  - No additional containers needed

#### Phase 2: Social OAuth Providers (Priority: MEDIUM)
- **Providers:**
  1. Microsoft (common for business users)
  2. Facebook (high consumer adoption)
  3. Apple (privacy-focused users, iOS ecosystem)
  4. GitHub (developer community)
- **Security:**
  - OAuth 2.0 with PKCE flow
  - State parameter validation (prevent CSRF)
  - Token storage: Encrypted at rest (AES-256)
  - Automatic token refresh before expiry
- **UX:**
  - Unified "Sign in with..." buttons
  - One-click account linking (merge accounts)
  - Provider preference saved per user
  - Clear privacy messaging per provider
- **Resources:**
  - Zero cost (all providers offer free OAuth)
  - +50MB RAM (OAuth library overhead)
  - OAuth tokens stored in existing database

#### Phase 3: Two-Factor Authentication (Priority: MEDIUM)
- **Methods:**
  - TOTP (Google Authenticator, Authy) - Priority
  - SMS backup codes (Twilio free tier: 15 SMS/month)
  - Recovery codes (10 one-time codes)
- **Security:**
  - Mandatory 2FA for admin/owner roles
  - Optional for view-only users
  - Backup codes encrypted in database
  - Rate limiting: 3 failed 2FA attempts = temporary lockout
- **UX:**
  - QR code setup (scan with authenticator app)
  - Test verification during setup
  - Download/print recovery codes
  - Remember device option (30 days)
- **Resources:**
  - TOTP library: pyotp (~1MB)
  - No external service needed (free)

---

## Feature 2: Email-to-Process

**Current State:** Manual upload only
**Target State:** Forward documents via email for automatic processing

### Objectives

#### Phase 1: Self-Hosted SMTP Server (Priority: HIGH)
- **Goal:** Accept emails at `{user_id}@docs.bonidoc.com` with zero cost
- **Architecture:**
  - Lightweight Python SMTP server (aiosmtpd)
  - Separate Docker container (256MB RAM limit)
  - Direct integration with existing batch processor
- **Security:**
  - Whitelist: Only accept from verified user email addresses
  - Virus scanning: ClamAV on all attachments (already installed)
  - Rate limiting: 50 emails/day per user, 20MB max per email
  - SPF/DKIM/DMARC records configured
  - Reject emails from unknown senders (prevent spam relay)
- **UX:**
  - Settings page: Display user's unique email address
  - Copy-to-clipboard button
  - Email template examples (subject line, body)
  - Notification: "We received your email" + processing status
  - Same confirmation flow as web upload
- **Resources:**
  - RAM: +100-150MB (SMTP server + email parsing)
  - Storage: Reuse existing /app/temp (2GB limit)
  - CPU: <1% (email parsing is lightweight)
  - Cost: $0 (self-hosted)

#### Phase 2: Email Forwarding Rules (Priority: MEDIUM)
- **Goal:** Users can forward from ANY email address (not just verified)
- **Security:**
  - Domain verification: Verify sender domain via SPF lookup
  - Content analysis: Scan for phishing/spam patterns
  - User approval: First-time sender requires manual approval
- **UX:**
  - Settings: Manage allowed senders list
  - Notification for new sender approval requests
  - Bulk approve/reject senders
- **Resources:**
  - No change (same infrastructure)

#### Phase 3: Email Processing Rules (Priority: LOW)
- **Goal:** Auto-categorize based on email metadata
- **Features:**
  - Subject line parsing: Extract category hints
  - Sender-based rules: "Always categorize emails from X as Y"
  - Attachment name patterns: "invoice*.pdf" → Invoices
- **UX:**
  - Settings: Create email processing rules
  - Visual rule builder (if sender = X, then category = Y)
  - Test rules before activation
- **Resources:**
  - No change (rule evaluation is lightweight)

---

## Feature 3: Folder Monitoring (Google Drive)

**Current State:** Manual upload only
**Target State:** Auto-process new files in designated Drive folder

### Objectives

#### Phase 1: Watch Folder Setup (Priority: HIGH)
- **Goal:** User designates a "Watch Folder" in Google Drive
- **Architecture:**
  - Google Drive API push notifications (webhooks)
  - Celery background task: Monitor for new files
  - Process new files → Move to categorized folders
- **Security:**
  - OAuth scope: drive.file (read-only access to specific folder)
  - Webhook validation: Verify Google signature
  - File hash tracking: Avoid re-processing duplicates
- **UX:**
  - Settings: "Choose Watch Folder" button (Drive picker UI)
  - Visual indicator: "Watching: /Documents/Inbox"
  - Notification: "3 new documents processed from Watch Folder"
  - Option to disable/change folder anytime
- **Resources:**
  - RAM: +50MB (webhook handler)
  - Storage: No change (files stay in Drive)
  - CPU: <1% (file detection logic)
  - Cost: $0 (Google Drive API is free)

#### Phase 2: Multiple Watch Folders (Priority: MEDIUM)
- **Goal:** Support 2-3 watch folders per user (Starter: 1, Pro: 3)
- **Features:**
  - Different folders for different purposes (Invoices, Receipts, Contracts)
  - Per-folder category mapping (optional)
- **UX:**
  - Settings: Add/remove watch folders
  - Per-folder status: Active | Paused | Error
- **Resources:**
  - +minimal (scale linearly with folder count)

#### Phase 3: Folder Processing Rules (Priority: LOW)
- **Goal:** Advanced automation based on folder structure
- **Features:**
  - Subfolder-based categorization: /Invoices/2024/ → Invoices category
  - Filename pattern matching: Similar to email rules
  - Schedule-based processing: Only process during business hours
- **UX:**
  - Advanced settings: Rule configuration UI
  - Preview mode: Show what would be processed without actually processing
- **Resources:**
  - No change (rule evaluation is lightweight)

---

## Feature 4: Multi-User Access & Permissions

**Current State:** Single user per account
**Target State:** Share documents with team members (view/admin/owner roles)

### Objectives

#### Phase 1: Permission Model Design (Priority: CRITICAL)
- **Roles:**
  1. **Owner:** Full control (original account holder)
     - Manage billing
     - Add/remove users
     - Delete all documents
     - Transfer ownership
  2. **Admin:** Manage content (team managers)
     - Upload/edit/delete documents
     - Manage categories
     - Manage other users (except owner)
     - Cannot access billing
  3. **Editor:** Modify documents (active contributors)
     - Upload/edit documents
     - Cannot delete others' documents
     - Cannot manage users
  4. **Viewer:** Read-only (auditors, stakeholders)
     - View/download documents
     - Search and filter
     - Cannot upload or modify
- **Cloud Storage Model:**
  - **Owner's Cloud:** Documents stored in owner's Google Drive
  - **Shared Access:** Other users access via Bonifatus app (not direct Drive access)
  - **Advantage:** Owner retains full control and ownership
  - **Trade-off:** Users don't see documents in their own Drive (by design)

#### Phase 2: User Invitation System (Priority: HIGH)
- **Goal:** Owner/Admin can invite team members
- **Security:**
  - Email invitation with time-limited token (7 days expiry)
  - Invitee must accept invitation
  - Invitation revocation (before acceptance)
  - Invited user must verify email
- **UX:**
  - Settings → Team Management → "Invite User"
  - Enter email + assign role
  - Track invitation status: Pending | Accepted | Expired
  - Resend invitation button
  - Bulk invite (CSV upload) for Pro tier
- **Resources:**
  - Database: New tables (invitations, user_roles, team_members)
  - RAM: +minimal (query overhead)
  - Storage: +negligible

#### Phase 3: Document Access Control (Priority: HIGH)
- **Access Levels:**
  - **Team-wide:** All team members can access (default for shared docs)
  - **Private:** Only owner + specific users can access
  - **Public link:** Generate shareable link (optional: password-protected)
- **Security:**
  - Row-level security: Database queries filtered by user permissions
  - Document visibility checks on every API request
  - Audit log: Track who accessed which documents
- **UX:**
  - Document detail page: "Share with team" toggle
  - Select specific users for private documents
  - Generate public link with expiry date
  - Visual indicator: 🔒 Private | 👥 Team | 🌐 Public
- **Resources:**
  - Database: Permission checks add minimal overhead (<5ms per query)
  - No additional infrastructure needed

#### Phase 4: Team Activity Audit Log (Priority: MEDIUM)
- **Goal:** Track all team member actions for compliance
- **Logged Actions:**
  - Document uploaded/edited/deleted (who, when, which doc)
  - User added/removed/role changed
  - Category created/modified
  - Bulk operations performed
- **UX:**
  - Admin dashboard: Activity log viewer
  - Filter by: User, action type, date range
  - Export to CSV (for compliance reporting)
- **Resources:**
  - Database: New audit_logs table
  - Storage: ~1KB per log entry (~100MB for 100K actions)
  - Retention: 12 months (configurable)

#### Phase 5: Usage Limits per Role (Priority: MEDIUM)
- **Goal:** Enforce tier limits across team (not per user)
- **Limits:**
  - **Documents/month:** Shared across team
  - **Storage:** Shared (owner's Drive quota)
  - **API calls:** Shared rate limit
- **Example (Starter Tier):**
  - 1 owner + 2 viewers = 500 docs/month (shared)
  - If any user uploads 300 docs, only 200 remain for team
- **UX:**
  - Dashboard: Team usage meter (docs used: 230/500)
  - Notification when 80% quota reached
  - Upgrade prompt when limit hit
- **Resources:**
  - Database: Usage tracking table (updated on every upload)
  - +minimal overhead

---

## Feature 5: Multi-Cloud Support

**Current State:** Google Drive only
**Target State:** Dropbox, OneDrive, Box

### Objectives

#### Phase 1: Cloud Storage Abstraction Layer (Priority: CRITICAL)
- **Goal:** Unified interface for all cloud providers
- **Architecture:**
  - Abstract class: CloudStorageProvider
  - Implementations: GoogleDriveProvider, DropboxProvider, OneDriveProvider, BoxProvider
  - Common operations: upload, download, list, delete, create_folder
- **Security:**
  - OAuth tokens encrypted at rest (AES-256)
  - Token rotation: Automatic refresh before expiry
  - Separate credentials per provider
- **UX:**
  - No change from user perspective (seamless)
- **Resources:**
  - Code abstraction: +10-15% CPU overhead (negligible)
  - No additional storage

#### Phase 2: Dropbox Integration (Priority: HIGH)
- **Goal:** Users can connect Dropbox instead of Google Drive
- **OAuth Scopes:**
  - files.content.read
  - files.content.write
  - files.metadata.read
- **Features:**
  - Full upload/download/organize functionality
  - Folder monitoring (via Dropbox webhooks)
- **UX:**
  - Settings: "Connect Dropbox" button
  - Switch between providers (one active at a time)
  - Visual indicator: Current provider badge
- **Resources:**
  - +50MB RAM (Dropbox SDK)
  - Cost: $0 (Dropbox API is free)

#### Phase 3: OneDrive Integration (Priority: HIGH)
- **Goal:** Support Microsoft OneDrive (business users)
- **OAuth Scopes:**
  - Files.ReadWrite.All
  - User.Read
- **Features:**
  - Same as Dropbox
- **UX:**
  - Same as Dropbox
- **Resources:**
  - +50MB RAM (Microsoft Graph SDK)
  - Cost: $0 (OneDrive API is free)

#### Phase 4: Box Integration (Priority: MEDIUM)
- **Goal:** Support Box.com (enterprise users)
- **OAuth Scopes:**
  - root_readwrite
  - manage_enterprise_properties
- **Features:**
  - Same as Dropbox/OneDrive
- **UX:**
  - Same as Dropbox/OneDrive
- **Resources:**
  - +50MB RAM (Box SDK)
  - Cost: $0 (Box API is free)

#### Phase 5: Multi-Cloud Sync (Priority: LOW - Future)
- **Goal:** Sync documents across multiple cloud providers simultaneously
- **Use Case:** Backup to secondary cloud (e.g., Google Drive primary, Dropbox backup)
- **Complexity:** HIGH (conflict resolution, bandwidth)
- **Resources:**
  - +significant RAM/bandwidth (syncing files)
  - Consider as post-MVP feature

---

## Resource Budget Summary

| Feature | RAM Impact | Storage Impact | CPU Impact | Cost |
|---------|-----------|----------------|-----------|------|
| **Email/Password Auth** | +10MB | +negligible | <1% | $0 |
| **Social OAuth (4 providers)** | +50MB | +negligible | <1% | $0 |
| **2FA (TOTP)** | +5MB | +negligible | <1% | $0 |
| **Email-to-Process** | +100MB | +100MB temp | <1% | $0 |
| **Folder Monitoring** | +50MB | +0MB | <1% | $0 |
| **Multi-User Access** | +20MB | +10MB (logs) | <2% | $0 |
| **Dropbox** | +50MB | +0MB | <1% | $0 |
| **OneDrive** | +50MB | +0MB | <1% | $0 |
| **Box** | +50MB | +0MB | <1% | $0 |
| **TOTAL** | **+385MB** | **+110MB** | **<8%** | **$0** |

**Current Available Resources:**
- RAM: 2.5GB available → **Sufficient** (using only 15%)
- Storage: 25GB available → **Sufficient** (using <1%)
- CPU: <5% used → **Sufficient** (total <13% after all features)

**Conclusion:** All features can be implemented with ZERO additional infrastructure cost.

---

## Implementation Priority

### Phase 1 (Month 1) - Core Enablers
1. ✅ Email/Password Authentication (Week 1-2)
2. ✅ Email-to-Process (Week 2-3)
3. ✅ Multi-User Permissions Model (Week 3-4)

### Phase 2 (Month 2) - User Growth
4. ✅ User Invitation System (Week 1)
5. ✅ Folder Monitoring (Week 2)
6. ✅ Social OAuth (2 providers: Microsoft, Facebook) (Week 3)
7. ✅ Document Access Control (Week 4)

### Phase 3 (Month 3) - Enterprise Features
8. ✅ 2FA (TOTP) (Week 1)
9. ✅ Dropbox Integration (Week 2)
10. ✅ OneDrive Integration (Week 3)
11. ✅ Activity Audit Log (Week 4)

### Phase 4 (Month 4) - Polish & Scale
12. ✅ Box Integration (Week 1)
13. ✅ Advanced Email/Folder Rules (Week 2-3)
14. ✅ Usage Analytics Dashboard (Week 4)

---

## Security Best Practices

### Authentication
- Passwords: bcrypt (12+ rounds), minimum 12 characters
- Sessions: 30-day expiry, secure httpOnly cookies
- Rate limiting: 5 failed attempts = 15min lockout
- CAPTCHA: hCaptcha after 3 failed attempts

### OAuth
- PKCE flow for all providers
- State parameter validation (CSRF protection)
- Token encryption at rest (AES-256)
- Automatic token refresh

### Email Processing
- SPF/DKIM/DMARC validation
- Virus scanning (ClamAV) on all attachments
- Sender whitelist enforcement
- Rate limiting per user

### Multi-User Access
- Row-level security in database
- Permission checks on every API request
- Audit logging for compliance
- Invite token expiry (7 days)

### Cloud Storage
- OAuth scopes: Minimal required permissions
- Token encryption at rest
- Automatic token rotation
- Provider-specific security (Box SSO, etc.)

---

## UX Principles

### Simplicity
- One-click operations where possible
- Minimal configuration required
- Smart defaults (e.g., suggested categories)

### Transparency
- Clear permission explanations
- Processing status notifications
- Usage quota visibility

### Flexibility
- Multiple authentication methods
- Choose preferred cloud provider
- Granular access control

### Reliability
- Graceful error handling
- Retry failed operations
- Email/notification confirmations

---

## Success Metrics

### Feature Adoption
- % users enabling email-to-process (Target: 40%)
- % users enabling folder monitoring (Target: 30%)
- % teams with 2+ users (Target: 20%)
- % users connecting 2+ cloud providers (Target: 10%)

### Performance
- Email processing latency: <30 seconds
- Folder monitoring delay: <5 minutes
- Multi-user query overhead: <5ms
- Cloud provider API success rate: >99%

### Security
- Zero security incidents
- 100% virus scanning coverage
- <0.1% false positive rate (spam detection)
- Full audit trail coverage

---

## Next Steps

1. Review and approve roadmap priorities
2. Assign implementation order
3. Begin Phase 1 development
4. Set up monitoring/analytics for metrics tracking
5. Prepare marketing materials for each feature launch

---

**End of Document**
