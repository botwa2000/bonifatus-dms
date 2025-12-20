# Multi-User Delegate Access - Document Viewing Implementation

**Status:** In Progress - Implementing multi-select filter for unified document view

**Last Updated:** 2025-12-20

---

## Overview

Delegates can now accept invitations, but cannot yet view the owner's documents. This phase implements document access with a flexible multi-select filter approach.

---

## Design Concept

**Multi-Select Filter with Unified View:**
- Users can check which document sources to view (own documents and/or shared documents)
- All selected documents appear in one unified list
- Visual indicators (icons, background colors) distinguish own vs shared documents
- Edit/delete buttons are greyed out for shared documents (read-only access)
- Universal search works across all selected document sources

---

## User Experience

### For Delegates (Document Viewers)

**Filter Panel:**
```
📂 Document Sources
☑ My Documents
☑ Shared: Alexander Perel
☐ Shared: John Doe
[Apply Filters]
```

**Document List:**
```
📄 Invoice.pdf              👤 My Document
   [View] [Edit] [Download] [Delete]

📄 Contract.pdf         🔗 Alexander Perel
   [View] [Edit] [Download] [Delete]  ← Edit/Delete greyed out
          ↑ tooltip: "Cannot edit shared documents"

📄 Report.pdf               👤 My Document
   [View] [Edit] [Download] [Delete]
```

**Visual Indicators:**
- `👤` icon = My Document (your own)
- `🔗` icon = Shared document (owner name shown)
- Light blue background for shared documents
- Owner name badge on shared documents
- Greyed out edit/delete buttons with helpful tooltips

---

## Implementation Milestones

### Phase 1: Backend - Multi-Source Document Fetching
- [ ] Modify GET /documents endpoint to accept multiple source parameters
- [ ] Add `include_own` boolean parameter
- [ ] Add `include_shared` parameter (comma-separated owner IDs)
- [ ] Validate delegate has active access to each requested owner
- [ ] Merge documents from all sources into single response
- [ ] Add owner metadata to each document (owner_type, owner_name, can_edit, can_delete)

### Phase 2: Backend - Permission Enforcement
- [ ] Add permission checks for each shared document source
- [ ] Set can_edit=false and can_delete=false for shared documents
- [ ] Add owner_user_id and owner_name to document response
- [ ] Ensure download is allowed for shared documents (read-only access)

### Phase 3: Frontend - Filter Panel Component
- [ ] Create DocumentSourceFilter component
- [ ] Load granted access list on mount
- [ ] Render checkbox for "My Documents"
- [ ] Render checkbox for each owner who granted access
- [ ] Track selected sources in state
- [ ] Apply filter button triggers document reload

### Phase 4: Frontend - Document List Updates
- [ ] Modify document list to show owner indicators
- [ ] Add owner icon (👤 for own, 🔗 for shared)
- [ ] Add owner name badge for shared documents
- [ ] Apply light blue background to shared documents
- [ ] Update document card styling

### Phase 5: Frontend - Permission-Based UI
- [ ] Grey out edit button for shared documents
- [ ] Grey out delete button for shared documents
- [ ] Add tooltips explaining read-only restrictions
- [ ] Keep view and download enabled for shared documents
- [ ] Test button states for own vs shared documents

### Phase 6: Universal Search Integration
- [ ] Ensure search works across all visible documents
- [ ] Search respects current filter selection
- [ ] Search results maintain owner indicators
- [ ] Test search with mixed own/shared documents

### Phase 7: Document Detail View
- [ ] Update document detail page to show owner info
- [ ] Disable edit mode for shared documents
- [ ] Show read-only banner on shared document pages
- [ ] Ensure download works for shared documents

### Phase 8: Testing & Polish
- [ ] Test filter combinations (own only, shared only, both)
- [ ] Test with multiple shared sources
- [ ] Verify permission enforcement (cannot edit shared)
- [ ] Test search across mixed sources
- [ ] Verify visual indicators are clear
- [ ] Test on mobile/responsive view

---

## Current Status

### ✅ Completed (Previous Phases)
- Database schema with unique constraints
- User validation (invitees must have BoniDoc accounts)
- Invite/accept/decline API endpoints
- Settings page "Team Access" section (for Pro users)
- Settings page "Shared with Me" section (for delegates)
- Email invitation system
- Pending invitations notification on dashboard
- Timezone-aware datetime handling

### 🚧 In Progress
- Multi-select filter for document sources
- Unified document view with permission indicators

### ❌ Not Started
- Document download with delegate access logging
- Audit trail for delegate document access
- Admin dashboard for monitoring delegate activity

---

## Technical Notes

### API Changes
```
GET /api/v1/documents?include_own=true&include_shared=owner1,owner2
```

### Response Structure
```json
{
  "documents": [
    {
      "id": "...",
      "title": "Invoice.pdf",
      "owner_type": "own",
      "can_edit": true,
      "can_delete": true
    },
    {
      "id": "...",
      "title": "Contract.pdf",
      "owner_type": "shared",
      "owner_user_id": "...",
      "owner_name": "Alexander Perel",
      "can_edit": false,
      "can_delete": false
    }
  ]
}
```

---

## Priority Order

1. **HIGH:** Backend multi-source document fetching
2. **HIGH:** Permission enforcement and metadata
3. **HIGH:** Filter panel component
4. **HIGH:** Document list UI updates
5. **MEDIUM:** Universal search integration
6. **MEDIUM:** Document detail page updates
7. **LOW:** Audit logging for delegate access
8. **LOW:** Admin monitoring dashboard

---

**Next Steps:** Implement backend multi-source document fetching with permission validation.
