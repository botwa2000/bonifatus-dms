# Analytics Quick Start - Test in 5 Minutes

## ✅ What's Already Done

Analytics is **fully implemented** in your code:

- ✅ Google Analytics 4 configured (ID: G-4ZJWP2FWRZ)
- ✅ PostHog ready (just needs API key to enable)
- ✅ Plausible ready (optional)
- ✅ Development testing enabled
- ✅ Automatic event tracking for:
  - User signup/login/logout
  - Document uploads/downloads/deletions
  - Subscription conversions
  - Delegate invitations

## 🚀 Test Right Now (5 Minutes)

### 1. Start Your Dev Server
```bash
cd frontend
npm run dev
```

### 2. Open Your Browser
```
http://localhost:3000
```

### 3. Open Browser Console
Press **F12** → Click **Console** tab

### 4. Look for Analytics Logs
You should see:
```
[Analytics DEV] Pageview: /
[Analytics DEV] Pageview: /dashboard
```

### 5. Check Google Analytics Real-Time
1. Go to [Google Analytics](https://analytics.google.com)
2. Click **Reports** → **Realtime**
3. You should see **1 active user** (you!)
4. Under "Event count by Event name" you should see:
   - `page_view`
   - `session_start`

**If you see this → Analytics is working! 🎉**

---

## 🔍 What Events Are Tracked?

### Already Tracking (No code needed):
| Event | When It Fires | What It Tracks |
|-------|--------------|----------------|
| `page_view` | Every page load | Page URL, title |
| `session_start` | User lands on site | New session |
| `first_visit` | User's first time | New user |
| `scroll` | User scrolls 90% | Engagement |
| `click` | Outbound link clicked | External traffic |
| `file_download` | Document downloaded | File name, size |

### Custom Events (Built into your code):
| Event | When It Fires | Parameters |
|-------|--------------|------------|
| `signup` | User registers | `method: 'google' or 'email'` |
| `login` | User logs in | `method: 'google' or 'email'` |
| `logout` | User logs out | - |
| `document_upload` | File uploaded | `file_type`, `file_size_kb` |
| `document_view` | Document opened | `document_id` |
| `document_download` | Download clicked | `document_id`, `file_type` |
| `document_delete` | Document deleted | `document_id` |
| `document_search` | Search performed | `query`, `results_count` |
| `subscription_start` | Subscribe clicked | `tier`, `billing_cycle` |
| `purchase` | Payment completed | `value`, `currency`, `transaction_id` |
| `subscription_complete` | Subscription confirmed | `tier`, `billing_cycle`, `amount` |
| `subscription_cancel` | User cancels | `tier`, `reason` |
| `delegate_invite` | Delegate invited | `role` |
| `delegate_accept` | Invite accepted | `owner_name`, `role` |

---

## 📊 How to View Analytics Data

### Real-Time (Instant):
1. **Reports → Realtime**
   - See active users right now
   - Events happening in last 30 minutes

2. **Admin → DebugView**
   - Install [GA Debugger Extension](https://chrome.google.com/webstore/detail/google-analytics-debugger/jnkmfdileelhofjcijamephohjechhna)
   - See every event with all parameters
   - Best for testing!

### Historical (24-48 hours delay):
1. **Reports → Engagement → Events**
   - All events with counts
   - Mark events as conversions here

2. **Reports → Monetization → Overview**
   - Revenue from subscriptions
   - Requires `purchase` event marked as conversion

3. **Explore → Free form**
   - Custom reports
   - Combine any metrics and dimensions

---

## ⚙️ Google Analytics Setup (Required)

Follow these steps in order:

### Step 1: Enhanced Measurement (2 mins)
1. GA4 → **Admin** → **Data Streams**
2. Click your stream
3. Click **gear icon** next to "Enhanced measurement"
4. Enable all toggles → **Save**

### Step 2: Mark Conversions (After first events arrive)
1. **Admin** → **Events**
2. Wait for events to appear (test by using your app)
3. Toggle **"Mark as conversion"** for:
   - `purchase`
   - `signup`
   - `login`

### Step 3: Create Revenue Conversion (5 mins)
See **ANALYTICS_SETUP.md → Step 5** for detailed instructions

This creates a `subscription_complete` event that tracks revenue properly.

### Step 4: Exclude Localhost (Recommended)
1. **Admin** → **Data Settings** → **Data Filters**
2. Create filter:
   - Name: `Exclude Development`
   - Type: `Developer traffic`
   - Condition: `page_location` contains `localhost`
   - State: **Active**

---

## 🎯 Quick Win: Create Your First Funnel

See where users drop off in subscription flow:

1. GA4 → **Explore** → **Blank**
2. Select **Funnel exploration**
3. Add steps:
   - Step 1: `first_visit`
   - Step 2: `signup`
   - Step 3: `subscription_start`
   - Step 4: `purchase`
4. **Apply** → **Save as "Subscription Funnel"**

**This shows:**
- % of visitors who sign up
- % of signups who try to subscribe
- % who complete payment
- Where you're losing potential customers

---

## 🐛 Troubleshooting

### "No events in Real-Time"
1. Check console for `[Analytics DEV]` logs
2. If missing, restart dev server: `npm run dev`
3. Clear browser cache
4. Disable ad blockers

### "Events in console but not in GA4"
1. Wait 30 seconds (GA4 has delay)
2. Check Network tab for `google-analytics.com` requests
3. Verify measurement ID in URL: `G-4ZJWP2FWRZ`

### "Can't find DebugView"
1. Install [GA Debugger Extension](https://chrome.google.com/webstore/detail/google-analytics-debugger/jnkmfdileelhofjcijamephohjechhna)
2. Click extension (turns blue)
3. GA4 → **Admin** → **DebugView** (left sidebar)

---

## 📚 Full Documentation

For complete setup guide: **See ANALYTICS_SETUP.md**

Includes:
- Step-by-step GA4 configuration
- Custom dimensions setup
- Audience creation
- BigQuery export
- PostHog and Plausible setup
- Advanced troubleshooting

---

## ✅ Checklist

- [ ] Start dev server, open localhost
- [ ] See `[Analytics DEV]` in console
- [ ] Check GA4 Realtime - see your pageview
- [ ] Navigate to a few pages
- [ ] Check Realtime - see multiple events
- [ ] Enable Enhanced Measurement in GA4
- [ ] Mark `purchase`, `signup`, `login` as conversions
- [ ] Create subscription funnel
- [ ] Exclude localhost from production data

**Once this checklist is done → Analytics is production-ready! 🎉**

---

## 🚀 Next Steps

1. **Today:** Test in development (this guide)
2. **This week:** Configure GA4 (Enhanced Measurement, conversions)
3. **Before launch:** Test full user journey (signup → subscribe → upload)
4. **After launch:** Monitor Real-Time daily, check funnels weekly
5. **Optional:** Sign up for PostHog for session recordings

---

**Questions?** Check ANALYTICS_SETUP.md or [GA4 Help](https://support.google.com/analytics)
