# Email Templates Master Document

**Purpose:** This document defines all email communications sent by BoniDoc. It clearly separates hardcoded text (what users see) from dynamic variables (pulled from database).

**Legend:**
- `{{variable}}` = Dynamic value from database
- Regular text = Hardcoded message content
- 📧 = Email type
- 🔄 = When triggered
- 📝 = Variables used

---

## 1. ACCOUNT & AUTHENTICATION

### 📧 1.1 Welcome Email
**Template Name:** `welcome_email`
**🔄 Trigger:** User creates account (OAuth or email signup)
**Subject:** Welcome to BoniDoc!

**📝 Variables:**
- `{{user_name}}` - User's full name or email
- `{{login_url}}` - Link to login page

**Email Content:**
```
Hi {{user_name}},

Welcome to BoniDoc! Your account has been created successfully.

You can now log in and start organizing your documents:
[Button: Go to Login] → {{login_url}}

If you have any questions, feel free to contact our support team.

Best regards,
The BoniDoc Team
```

**Hardcoded Text:**
- "Welcome to BoniDoc!"
- "Your account has been created successfully"
- "You can now log in and start organizing your documents"
- "If you have any questions, feel free to contact our support team"
- "Best regards, The BoniDoc Team"

---

### 📧 1.2 Password Reset
**Template Name:** `password_reset`
**🔄 Trigger:** User requests password reset
**Subject:** Reset Your BoniDoc Password

**📝 Variables:**
- `{{user_name}}` - User's full name
- `{{reset_url}}` - Password reset link with token

**Email Content:**
```
Hi {{user_name}},

You requested to reset your BoniDoc password.

Click the link below to reset your password:
[Button: Reset Password] → {{reset_url}}

This link will expire in 24 hours.

If you didn't request this, please ignore this email - your password will remain unchanged.

Best regards,
The BoniDoc Team
```

**Hardcoded Text:**
- "You requested to reset your BoniDoc password"
- "This link will expire in 24 hours"
- "If you didn't request this, please ignore this email"

---

### 📧 1.3 Two-Factor Verification Code
**Template Name:** `verification_code`
**🔄 Trigger:** User attempts login with 2FA enabled
**Subject:** Your BoniDoc Verification Code

**📝 Variables:**
- `{{user_name}}` - User's full name
- `{{verification_code}}` - 6-digit code
- `{{code_expiration_minutes}}` - Code validity period (e.g., "10", "15") - from database

**Email Content:**
```
Hi {{user_name}},

Your verification code is:

{{verification_code}}

This code will expire in {{code_expiration_minutes}} minutes.

If you didn't request this code, please secure your account immediately.

Best regards,
The BoniDoc Team
```

**Hardcoded Text:**
- "Your verification code is:"
- "This code will expire in ... minutes"
- "If you didn't request this code, please secure your account immediately"

---

## 2. SUBSCRIPTION LIFECYCLE

### 📧 2.1 Subscription Confirmation (New Subscription)
**Template Name:** `subscription_confirmation`
**🔄 Trigger:** User completes payment for new subscription
**Subject:** Welcome to {{plan_name}}!

**📝 Variables:**
- `{{user_name}}` - User's full name
- `{{plan_name}}` - Tier display name (e.g., "Starter", "Professional")
- `{{billing_cycle}}` - "Monthly" or "Yearly"
- `{{billing_period}}` - "month" or "year"
- `{{currency_display}}` - Formatted price (e.g., "$9.99" or "9.99 CHF")
- `{{next_billing_date}}` - Date of next charge (e.g., "December 23, 2025")
- `{{tier_feature_1}}` - First feature (e.g., "100 document uploads")
- `{{tier_feature_2}}` - Second feature (e.g., "10 GB cloud storage")
- `{{tier_feature_3}}` - Third feature (e.g., "Advanced search")
- `{{dashboard_url}}` - Link to user dashboard
- `{{support_url}}` - Link to support center

**Email Content:**
```
Hi {{user_name}},

Thank you for subscribing to BoniDoc! Your {{plan_name}} subscription is now active.

Subscription Details:
• Plan: {{plan_name}}
• Billing: {{billing_cycle}}
• Amount: {{currency_display}}/{{billing_period}}
• Next billing date: {{next_billing_date}}

Your Plan Includes:
• {{tier_feature_1}}
• {{tier_feature_2}}
• {{tier_feature_3}}

[Button: Go to Dashboard] → {{dashboard_url}}

Need help? Reply to this email or visit our support center.
→ {{support_url}}

Best regards,
The BoniDoc Team
```

**Hardcoded Text:**
- "Thank you for subscribing to BoniDoc!"
- "subscription is now active"
- "Subscription Details:"
- "Your Plan Includes:"
- "Need help? Reply to this email or visit our support center"

---

### 📧 2.2 Subscription Canceled
**Template Name:** `subscription_canceled`
**🔄 Trigger:** User cancels their subscription
**Subject:** Subscription Canceled

**📝 Variables:**
- `{{user_name}}` - User's full name
- `{{plan_name}}` - Tier display name
- `{{cancellation_date}}` - Date canceled (e.g., "November 23, 2025")
- `{{access_end_date}}` - Last day of access (e.g., "December 23, 2025")
- `{{reactivate_url}}` - Link to reactivate subscription

**Email Content:**
```
Hi {{user_name}},

Your {{plan_name}} subscription has been canceled.

Cancellation Details:
• Plan: {{plan_name}}
• Canceled on: {{cancellation_date}}
• Access until: {{access_end_date}}

You will continue to have access to your subscription benefits until {{access_end_date}}.

Changed your mind? You can reactivate your subscription anytime:
[Button: Reactivate Subscription] → {{reactivate_url}}

We're sorry to see you go. If you have feedback on how we can improve, please reply to this email.

Best regards,
The BoniDoc Team
```

**Hardcoded Text:**
- "Your subscription has been canceled"
- "Cancellation Details:"
- "You will continue to have access to your subscription benefits until"
- "Changed your mind? You can reactivate your subscription anytime"
- "We're sorry to see you go. If you have feedback on how we can improve, please reply to this email"

---

### 📧 2.3 Billing Cycle Change Scheduled
**Template Name:** `billing_cycle_scheduled`
**🔄 Trigger:** User schedules change from monthly↔yearly
**Subject:** Billing Cycle Change Scheduled

**📝 Variables:**
- `{{user_name}}` - User's full name
- `{{current_cycle}}` - Current billing (e.g., "Monthly")
- `{{new_cycle}}` - New billing (e.g., "Yearly")
- `{{effective_date}}` - When change takes effect (e.g., "December 23, 2025")
- `{{currency_display}}` - Formatted new price (e.g., "$99.99" or "99.99 CHF")
- `{{manage_url}}` - Link to subscription management
- `{{support_url}}` - Link to support

**Email Content:**
```
Hi {{user_name}},

Your billing cycle change has been scheduled successfully.

Change Details:
• Current: {{current_cycle}}
• Changing to: {{new_cycle}}
• Effective: {{effective_date}}

Your next payment of {{currency_display}} will be charged on {{effective_date}}.

[Button: Manage Subscription] → {{manage_url}}

Questions? Reply to this email or visit our support center.
→ {{support_url}}

Best regards,
The BoniDoc Team
```

**Hardcoded Text:**
- "Your billing cycle change has been scheduled successfully"
- "Change Details:"
- "Your next payment of ... will be charged on"
- "Questions? Reply to this email or visit our support center"

---

### 📧 2.4 Subscription Reactivated
**Template Name:** `subscription_reactivated`
**🔄 Trigger:** User reactivates canceled subscription
**Subject:** Welcome Back to {{plan_name}}!

**📝 Variables:**
- `{{user_name}}` - User's full name
- `{{plan_name}}` - Tier display name
- `{{billing_cycle}}` - Billing frequency
- `{{currency_display}}` - Formatted price (e.g., "$9.99" or "9.99 CHF")
- `{{billing_period}}` - "month" or "year"
- `{{next_billing_date}}` - Next charge date
- `{{dashboard_url}}` - Link to dashboard

**Email Content:**
```
Hi {{user_name}},

Welcome back! Your {{plan_name}} subscription has been reactivated.

Subscription Details:
• Plan: {{plan_name}}
• Billing: {{billing_cycle}}
• Amount: {{currency_display}}/{{billing_period}}
• Next billing date: {{next_billing_date}}

[Button: Go to Dashboard] → {{dashboard_url}}

We're glad to have you back!

Best regards,
The BoniDoc Team
```

**Hardcoded Text:**
- "Welcome back!"
- "subscription has been reactivated"
- "We're glad to have you back!"

---

## 3. PAYMENT & INVOICES

### 📧 3.1 Invoice Payment Successful
**Template Name:** `invoice_paid`
**🔄 Trigger:** Stripe webhook confirms payment
**Subject:** Payment Received - Thank You!

**📝 Variables:**
- `{{user_name}}` - User's full name
- `{{plan_name}}` - Tier display name
- `{{invoice_number}}` - Stripe invoice number
- `{{invoice_date}}` - Invoice creation date
- `{{currency_display}}` - Formatted amount (e.g., "$9.99" or "9.99 CHF")
- `{{period_start}}` - Billing period start (e.g., "November 23, 2025")
- `{{period_end}}` - Billing period end (e.g., "December 23, 2025")
- `{{invoice_url}}` - Link to Stripe invoice PDF
- `{{support_url}}` - Link to support

**Email Content:**
```
Hi {{user_name}},

We've successfully processed your payment for {{plan_name}}.

Invoice Details:
• Invoice #: {{invoice_number}}
• Date: {{invoice_date}}
• Amount: {{currency_display}}
• Billing Period: {{period_start}} - {{period_end}}

[Button: View Invoice] → {{invoice_url}}

Your subscription is active and you have full access to all features.

Questions about your invoice? Reply to this email or visit our support center.
→ {{support_url}}

Best regards,
The BoniDoc Team
```

**Hardcoded Text:**
- "We've successfully processed your payment for"
- "Invoice Details:"
- "Your subscription is active and you have full access to all features"
- "Questions about your invoice? Reply to this email or visit our support center"

---

### 📧 3.2 Payment Failed
**Template Name:** `payment_failed`
**🔄 Trigger:** Stripe webhook indicates failed payment
**Subject:** Payment Failed - Action Required

**📝 Variables:**
- `{{user_name}}` - User's full name
- `{{plan_name}}` - Tier display name
- `{{currency_display}}` - Formatted amount (e.g., "$9.99" or "9.99 CHF")
- `{{failure_reason}}` - Reason from Stripe (e.g., "Insufficient funds")
- `{{retry_date}}` - When Stripe will retry
- `{{update_payment_url}}` - Link to update payment method
- `{{support_url}}` - Link to support

**Email Content:**
```
Hi {{user_name}},

We were unable to process your payment for {{plan_name}}.

Payment Details:
• Amount: {{currency_display}}
• Reason: {{failure_reason}}
• We'll retry on: {{retry_date}}

To avoid service interruption, please update your payment method:
[Button: Update Payment Method] → {{update_payment_url}}

Need help? Reply to this email or visit our support center.
→ {{support_url}}

Best regards,
The BoniDoc Team
```

**Hardcoded Text:**
- "We were unable to process your payment for"
- "To avoid service interruption, please update your payment method"
- "Need help? Reply to this email or visit our support center"

---

### 📧 3.3 Payment Reminder (Upcoming)
**Template Name:** `payment_reminder`
**🔄 Trigger:** 3 days before next billing date
**Subject:** Upcoming Payment on {{billing_date}}

**📝 Variables:**
- `{{user_name}}` - User's full name
- `{{plan_name}}` - Tier display name
- `{{currency_display}}` - Formatted amount (e.g., "$9.99" or "9.99 CHF")
- `{{billing_date}}` - Date payment will be charged
- `{{payment_method}}` - Last 4 digits of card (e.g., "•••• 4242")
- `{{manage_url}}` - Link to subscription management

**Email Content:**
```
Hi {{user_name}},

This is a friendly reminder that your {{plan_name}} subscription will renew soon.

Payment Details:
• Amount: {{currency_display}}
• Billing Date: {{billing_date}}
• Payment Method: {{payment_method}}

No action needed - we'll automatically charge your payment method on {{billing_date}}.

Want to update your payment method or billing cycle?
[Button: Manage Subscription] → {{manage_url}}

Best regards,
The BoniDoc Team
```

**Hardcoded Text:**
- "This is a friendly reminder that your subscription will renew soon"
- "No action needed - we'll automatically charge your payment method on"
- "Want to update your payment method or billing cycle?"

---

## 4. SYSTEM NOTIFICATIONS

### 📧 4.1 Storage Quota Warning (80% Used)
**Template Name:** `storage_warning`
**🔄 Trigger:** User reaches 80% of storage quota
**Subject:** Storage Quota Warning

**📝 Variables:**
- `{{user_name}}` - User's full name
- `{{used_gb}}` - GB used (e.g., "8")
- `{{total_gb}}` - Total GB available (e.g., "10")
- `{{percentage}}` - Percentage used (e.g., "80")
- `{{upgrade_url}}` - Link to upgrade plans

**Email Content:**
```
Hi {{user_name}},

You've used {{percentage}}% of your storage quota ({{used_gb}} GB of {{total_gb}} GB).

To ensure you can continue uploading documents, consider upgrading to a plan with more storage.

[Button: View Upgrade Options] → {{upgrade_url}}

Best regards,
The BoniDoc Team
```

**Hardcoded Text:**
- "You've used ... of your storage quota"
- "To ensure you can continue uploading documents, consider upgrading to a plan with more storage"

---

### 📧 4.2 Storage Quota Exceeded
**Template Name:** `storage_exceeded`
**🔄 Trigger:** User reaches 100% of storage quota
**Subject:** Storage Quota Exceeded - Action Required

**📝 Variables:**
- `{{user_name}}` - User's full name
- `{{total_gb}}` - Total GB available
- `{{upgrade_url}}` - Link to upgrade plans
- `{{manage_url}}` - Link to manage documents

**Email Content:**
```
Hi {{user_name}},

You've reached your storage limit ({{total_gb}} GB).

You won't be able to upload new documents until you:
• Upgrade to a plan with more storage, or
• Delete some existing documents

[Button: Upgrade Plan] → {{upgrade_url}}
[Button: Manage Documents] → {{manage_url}}

Best regards,
The BoniDoc Team
```

**Hardcoded Text:**
- "You've reached your storage limit"
- "You won't be able to upload new documents until you:"
- "Upgrade to a plan with more storage, or"
- "Delete some existing documents"

---

### 📧 4.3 Document Upload Limit Warning
**Template Name:** `document_limit_warning`
**🔄 Trigger:** User reaches 80% of document upload limit
**Subject:** Document Upload Limit Warning

**📝 Variables:**
- `{{user_name}}` - User's full name
- `{{used_count}}` - Documents uploaded (e.g., "80")
- `{{total_count}}` - Max documents (e.g., "100")
- `{{percentage}}` - Percentage used (e.g., "80")
- `{{upgrade_url}}` - Link to upgrade plans

**Email Content:**
```
Hi {{user_name}},

You've uploaded {{used_count}} of {{total_count}} documents ({{percentage}}%).

To continue uploading, consider upgrading to a plan with a higher document limit.

[Button: View Upgrade Options] → {{upgrade_url}}

Best regards,
The BoniDoc Team
```

**Hardcoded Text:**
- "You've uploaded ... of ... documents"
- "To continue uploading, consider upgrading to a plan with a higher document limit"

---

## 5. SECURITY & ADMIN

### 📧 5.1 Unusual Login Activity
**Template Name:** `security_alert`
**🔄 Trigger:** Login from new device/location
**Subject:** New Login to Your BoniDoc Account

**📝 Variables:**
- `{{user_name}}` - User's full name
- `{{device}}` - Device type (e.g., "Chrome on Windows")
- `{{location}}` - City/Country (e.g., "Berlin, Germany")
- `{{login_time}}` - Timestamp
- `{{ip_address}}` - IP address
- `{{secure_account_url}}` - Link to security settings

**Email Content:**
```
Hi {{user_name}},

We detected a new login to your BoniDoc account:

Login Details:
• Device: {{device}}
• Location: {{location}}
• Time: {{login_time}}
• IP: {{ip_address}}

If this was you, no action needed.

If you don't recognize this activity, secure your account immediately:
[Button: Secure My Account] → {{secure_account_url}}

Best regards,
The BoniDoc Team
```

**Hardcoded Text:**
- "We detected a new login to your BoniDoc account"
- "If this was you, no action needed"
- "If you don't recognize this activity, secure your account immediately"

---

### 📧 5.2 Account Deletion Confirmation
**Template Name:** `account_deleted`
**🔄 Trigger:** User deletes their account (GDPR)
**Subject:** Account Deletion Confirmed

**📝 Variables:**
- `{{user_name}}` - User's full name
- `{{deletion_date}}` - Date account was deleted
- `{{data_retention_days}}` - Days until permanent deletion (e.g., "30")

**Email Content:**
```
Hi {{user_name}},

Your BoniDoc account has been scheduled for deletion as of {{deletion_date}}.

Your data will be permanently deleted in {{data_retention_days}} days. During this period, you can still recover your account by logging in.

After {{data_retention_days}} days, all your data will be permanently removed and cannot be recovered.

We're sorry to see you go. If you have any feedback, please reply to this email.

Best regards,
The BoniDoc Team
```

**Hardcoded Text:**
- "Your BoniDoc account has been scheduled for deletion"
- "Your data will be permanently deleted in ... days"
- "During this period, you can still recover your account by logging in"
- "After ... days, all your data will be permanently removed and cannot be recovered"
- "We're sorry to see you go. If you have any feedback, please reply to this email"

---

## SUMMARY TABLE

| # | Template Name | Trigger | Variables Count | Status |
|---|---------------|---------|-----------------|--------|
| 1.1 | `welcome_email` | Account created | 2 | ✅ Exists |
| 1.2 | `password_reset` | Password reset request | 2 | ✅ Exists |
| 1.3 | `verification_code` | 2FA login | 3 (added expiration) | ✅ Exists (needs update) |
| 2.1 | `subscription_confirmation` | New subscription | 11 (currency_display) | ✅ Exists (needs simplification) |
| 2.2 | `subscription_canceled` | Subscription canceled | 5 | ✅ Exists (needs simplification) |
| 2.3 | `billing_cycle_scheduled` | Billing cycle change | 7 (currency_display) | ❌ Missing |
| 2.4 | `subscription_reactivated` | Subscription reactivated | 7 (currency_display) | ❌ Missing |
| 3.1 | `invoice_paid` | Payment successful | 9 (currency_display) | ✅ Exists (needs simplification) |
| 3.2 | `payment_failed` | Payment failed | 7 (currency_display) | ❌ Missing |
| 3.3 | `payment_reminder` | 3 days before billing | 6 (currency_display) | ❌ Missing |
| 4.1 | `storage_warning` | 80% storage used | 5 | ❌ Missing |
| 4.2 | `storage_exceeded` | 100% storage used | 4 | ❌ Missing |
| 4.3 | `document_limit_warning` | 80% docs uploaded | 5 | ❌ Missing |
| 5.1 | `security_alert` | Unusual login | 6 | ❌ Missing |
| 5.2 | `account_deleted` | Account deletion | 3 | ❌ Missing |

---

## NOTES

### Admin Editability
All templates stored in `email_templates` table with columns:
- `name` - Template identifier
- `subject` - Email subject (supports variables)
- `html_body` - HTML version (simplified format matching `welcome_email`)
- `text_body` - Plain text version
- `available_variables` - JSON array of allowed variables
- `is_active` - Enable/disable template

Admins can edit via admin panel at `/admin/email-templates`

### HTML Format Guidelines
To prevent spam filtering, use simple HTML structure matching `welcome_email`:
- ✅ Simple `<html><body>` structure
- ✅ Inline CSS for styling
- ✅ Minimal `<p>`, `<h2>`, `<a>` tags
- ❌ NO `<!DOCTYPE>`, `<head>`, `<meta>` tags
- ❌ NO complex `<div>` nesting
- ❌ NO tables for layout
- ❌ NO background images or embedded images

### Variable Naming Convention
- Use lowercase with underscores: `{{user_name}}`
- Be descriptive: `{{next_billing_date}}` not `{{date}}`
- Dates: Format as "Month DD, YYYY" in code before passing to template

### Currency Formatting Logic

**Problem:** Some currencies have symbols ($, €, £), others use codes (CHF, PLN, SEK).

**Solution:** Use `{{currency_display}}` which intelligently combines symbol/code with amount.

**Backend Logic (in email service):**
```python
# If currency has a symbol (from database)
if currency_obj.symbol:
    currency_display = f"{currency_obj.symbol}{amount}"  # "$9.99"
else:
    currency_display = f"{amount} {currency_obj.code}"  # "9.99 CHF"
```

**Variables for Currency Display:**
- `{{currency_display}}` - Formatted price (e.g., "$9.99" or "9.99 CHF") **[RECOMMENDED]**
- `{{amount}}` - Raw number (e.g., "9.99")
- `{{currency_code}}` - 3-letter code (e.g., "USD", "CHF")
- `{{currency_symbol}}` - Symbol if exists (e.g., "$", "€") or empty string

**Example Email Text:**
```
Amount: {{currency_display}}/{{billing_period}}
```
**Output:**
- With symbol: "Amount: $9.99/month"
- Without symbol: "Amount: 9.99 CHF/month"

**Both look professional!**

### Missing Templates Priority
**High Priority (implement soon):**
- `payment_failed` - Critical for payment recovery
- `billing_cycle_scheduled` - User expects confirmation
- `subscription_reactivated` - User expects confirmation

**Medium Priority:**
- `payment_reminder` - Reduces failed payments
- `storage_warning` - Prevents quota issues

**Low Priority:**
- Security and quota exceeded templates
