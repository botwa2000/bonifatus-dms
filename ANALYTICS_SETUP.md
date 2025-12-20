# BoniDoc Analytics Setup Guide

## Overview

BoniDoc uses a multi-layered analytics approach to track user journeys, conversions, and product usage:

1. **Google Analytics 4** (Primary) - Core analytics and conversion tracking
2. **PostHog** (Optional) - Product analytics with session recordings
3. **Plausible** (Optional) - Privacy-friendly, GDPR-compliant analytics

---

## ✅ Google Analytics 4 Setup (COMPLETED)

Your GA4 Measurement ID: **G-4ZJWP2FWRZ**

### Complete Google Analytics 4 Setup (Step-by-Step):

#### Step 1: Configure Enhanced Measurement

1. Go to [Google Analytics](https://analytics.google.com)
2. Click **Admin** (gear icon, bottom left)
3. Under **Property** column → Click **Data Streams**
4. Click on your web stream (bonidoc.com)
5. Under "Enhanced measurement" section → Click the **gear icon** ⚙️
6. **Enable all toggles:**
   - ✅ **Page views** (Auto-tracked)
   - ✅ **Scrolls** (90% scroll depth)
   - ✅ **Outbound clicks** (Links to external sites)
   - ✅ **Site search** (URL query parameter tracking)
   - ✅ **Video engagement** (YouTube embeds)
   - ✅ **File downloads** (PDF, XLSX, DOCX, TXT, etc.)
7. Click **Save**

---

#### Step 2: Enable Debug Mode for Development Testing

1. In same **Data Streams** page
2. Scroll to **Additional settings** section
3. Click **Configure tag settings**
4. Click **Show all** under "Settings"
5. Scroll to **Debug mode**
6. Toggle **ON** for: *"Include debug data in reports from browsers with DebugView enabled"*
7. This allows localhost events to appear in real-time DebugView

---

#### Step 3: Mark Existing Events as Conversions

**IMPORTANT:** Our code already sends these events automatically. You just need to mark them as conversions.

1. Go to **Admin** → Under **Property** → **Events**
2. Wait 24-48 hours for events to appear (or test now, they'll appear within 30 seconds in real-time)
3. Once you see these events in the list, click **"Mark as conversion"** toggle for:

   ✅ **purchase** (Stripe checkout completion)
   ✅ **signup** (New user registration)
   ✅ **login** (User login)

**DO NOT create these events manually - they're already in your code!**

---

#### Step 4: Create Custom Conversion Events (ONLY IF NEEDED)

⚠️ **IMPORTANT ANSWER TO YOUR QUESTION:**

**When Google Analytics asks "Create event with or without code?"**
- **Choose: WITHOUT CODE** (recommended for most cases)
- This lets you create events based on existing events we're already tracking
- Example: Create a conversion when `document_upload` event fires

**When it asks "Measure by page or form submission?"**
- **Choose based on what you want to track:**
  - **PAGE:** Use for page-based conversions (e.g., "Thank You" page after signup)
  - **FORM SUBMISSION:** Use if you want to track specific form submissions
  - **FOR BONIDOC:** We're tracking events via code, so you won't use these options. Instead, you'll use **"Custom event"**

---

#### Step 5: Create Revenue Tracking Conversion (CRITICAL)

This tracks your subscription revenue properly:

1. Go to **Admin** → **Events**
2. Click **Create event** (blue button, top right)
3. Choose: **"Create a custom event"**

**Event Configuration:**

- **Custom event name:** `subscription_complete`
- **Matching conditions:**
  - Parameter: `event_name`
  - Operator: `equals`
  - Value: `purchase`

  **AND**

  - Parameter: `currency`
  - Operator: `is set`

- **Parameter configuration (add these):**
  - Click **Add parameter**
  - Parameter: `value` → Copy from source event: `value`
  - Parameter: `currency` → Copy from source event: `currency`
  - Parameter: `transaction_id` → Copy from source event: `transaction_id`

4. Click **Create**
5. Go back to **Events** list
6. Find `subscription_complete` and toggle **"Mark as conversion"**

**Why this is important:**
- Google Analytics tracks `purchase` event automatically
- But you want a separate conversion called `subscription_complete` for better reporting
- This creates it based on the existing `purchase` event

---

#### Step 6: Set Up Ecommerce Revenue Tracking

This ensures Stripe payments show up in revenue reports:

1. Go to **Admin** → **Property** → **Data display**
2. Toggle **ON**: *"Show advanced metrics"*
3. Go to **Property** → **Events**
4. Find the `purchase` event
5. Make sure it's marked as conversion ✅
6. Go to **Reports** → **Monetization** → **Overview**
7. You should see revenue data once subscriptions start coming in

---

#### Step 7: Create Engagement Funnels (Recommended)

Track user journey from landing → signup → subscription:

1. Go to **Explore** (left sidebar)
2. Click **Blank** template
3. Select **Funnel exploration**
4. **Configure your funnel:**

   **Step 1:** `first_visit` (First time user)
   **Step 2:** `signup` (User registered)
   **Step 3:** `subscription_start` (Clicked subscribe)
   **Step 4:** `purchase` (Completed payment)

5. **Settings:**
   - Funnel type: **Open funnel**
   - Step order: **Sequence matters** (users must complete steps in order)

6. Click **Apply** and **Save**

**This shows you:**
- How many visitors convert to signups
- How many signups start subscription process
- How many complete payment
- Where users drop off

---

#### Step 8: Set Up Custom Dimensions (Optional but Recommended)

Track user tier and other metadata:

1. Go to **Admin** → **Property** → **Custom definitions**
2. Click **Create custom dimension**

**Create these dimensions:**

**Dimension 1: User Tier**
- Dimension name: `User Tier`
- Scope: `User`
- Description: `Subscription tier (free/pro/enterprise)`
- Event parameter: `tier`
- Click **Save**

**Dimension 2: Document Type**
- Dimension name: `Document Type`
- Scope: `Event`
- Description: `Type of document uploaded`
- Event parameter: `file_type`
- Click **Save**

**Dimension 3: Billing Cycle**
- Dimension name: `Billing Cycle`
- Scope: `Event`
- Description: `Monthly or yearly billing`
- Event parameter: `billing_cycle`
- Click **Save**

Now you can segment reports by tier, document type, etc.

---

#### Step 9: Configure Audience Segmentation

Create audiences for remarketing:

1. Go to **Admin** → **Property** → **Audiences**
2. Click **New audience**

**Create these audiences:**

**Audience 1: Free Tier Users Who Upload Documents**
- Name: `Engaged Free Users`
- Include users who:
  - `tier` equals `free`
  - AND
  - `document_upload` event fired at least once in last 30 days
- Use for: Remarketing to convert to paid tier

**Audience 2: Pro Users Approaching Limits**
- Name: `Pro Users Heavy Usage`
- Include users who:
  - `tier` equals `pro`
  - AND
  - `document_upload` event fired at least 50 times in last 30 days
- Use for: Upsell to enterprise tier

**Audience 3: Cart Abandoners**
- Name: `Started Subscription But Didn't Complete`
- Include users who:
  - `subscription_start` event fired
  - BUT
  - `purchase` event NOT fired
  - Within last 7 days
- Use for: Email remarketing to complete subscription

---

#### Step 10: Link to Google Ads (Optional)

If you're running Google Ads:

1. Go to **Admin** → **Property** → **Google Ads Links**
2. Click **Link**
3. Select your Google Ads account
4. Enable:
   - ✅ Personalized advertising
   - ✅ Auto-tagging
   - ✅ Import conversions
5. Click **Link**

**Import your conversions to Google Ads:**
1. Go to Google Ads
2. Tools → Conversions
3. Click **Import** → **Google Analytics 4**
4. Select:
   - `purchase` (Track subscription revenue)
   - `signup` (Track registrations)
5. Set conversion value:
   - Use value from GA4: **YES** (shows actual subscription amount)

---

#### Step 11: Set Up Data Filters (CRITICAL)

Exclude internal traffic and localhost:

1. Go to **Admin** → **Data Settings** → **Data Filters**
2. Click **Create filter**

**Filter 1: Exclude Localhost**
- Filter name: `Exclude Development Traffic`
- Filter type: `Developer traffic`
- Filter state: `Active`
- Matching conditions:
  - Parameter: `page_location`
  - Operator: `contains`
  - Value: `localhost`
- Click **Create**

**Filter 2: Exclude Your IP (if you have static IP)**
- Filter name: `Exclude Internal Traffic`
- Filter type: `Internal traffic`
- Filter state: `Active`
- IP addresses: Add your office/home IP
- Click **Create**

---

#### Step 12: Configure BigQuery Export (Optional - Free Tier Available)

Export raw data to BigQuery for advanced analysis:

1. Go to **Admin** → **Property** → **BigQuery Links**
2. Click **Link**
3. Select your Google Cloud project (create one if needed)
4. **Data export options:**
   - ✅ Daily export
   - ✅ Streaming export (if you need real-time)
5. Click **Submit**

**Benefits:**
- SQL queries on raw event data
- Unlimited custom reports
- Machine learning on user behavior
- Free tier: 10GB storage, 1TB queries/month

---

## 🧪 Testing Analytics in Development

Analytics is **already enabled in your development environment** via `.env.local`:

```bash
NEXT_PUBLIC_ENABLE_ANALYTICS_DEV=true
```

### How to Test:

1. **Start the development server:**
   ```bash
   cd frontend
   npm run dev
   ```

2. **Open browser console** (F12)
   - You'll see logs like: `[Analytics DEV] Pageview: /dashboard`
   - Every tracked event will be logged

3. **View Real-Time Reports:**
   - Go to GA4 → Reports → Realtime
   - Perform actions on localhost
   - See events appear in real-time (may take 5-10 seconds)

4. **Use Google Analytics Debugger Extension:**
   - Install: [GA Debugger Chrome Extension](https://chrome.google.com/webstore/detail/google-analytics-debugger/jnkmfdileelhofjcijamephohjechhna)
   - See detailed event information in console

---

## 📊 What's Being Tracked

### Automatic Events:
- **Page Views** - Every page navigation
- **Scrolls** - Users scrolling 90% of page
- **File Downloads** - Document downloads
- **Outbound Clicks** - Links to external sites

### Custom Events:

#### Authentication
- `signup` - New user registration (Google/Email)
- `login` - User login (Google/Email)
- `logout` - User logout

#### Documents
- `document_upload` - Document uploaded (tracks file type, size)
- `document_view` - Document opened
- `document_download` - Document downloaded
- `document_delete` - Document deleted
- `document_search` - Search performed (tracks query, results count)

#### Subscriptions (CONVERSIONS)
- `subscription_start` - User clicked subscribe button
- `purchase` - Stripe payment completed (Enhanced Ecommerce)
- `subscription_complete` - Subscription confirmed
- `subscription_cancel` - User cancelled subscription

#### Collaboration
- `delegate_invite` - User invited a delegate
- `delegate_accept` - Delegate accepted invitation
- `delegate_view_documents` - Delegate viewed shared documents

#### Engagement
- `feature_use` - Any feature interaction

---

## 🚀 Production Deployment

### Environment Variables for Production (Vercel/Netlify):

```bash
# Google Analytics (Already configured)
NEXT_PUBLIC_GA_MEASUREMENT_ID=G-4ZJWP2FWRZ

# IMPORTANT: Do NOT set this in production
# NEXT_PUBLIC_ENABLE_ANALYTICS_DEV should NOT exist in prod env
```

Analytics will automatically:
- ✓ Enable in production (no dev logs)
- ✓ Respect user's "Do Not Track" setting
- ✓ Anonymize IP addresses
- ✓ Use secure cookies

---

## 📈 Viewing Analytics Data

### Google Analytics 4:

1. **Real-Time Reports:**
   - See current active users
   - View live events as they happen
   - GA4 → Reports → Realtime

2. **Engagement Reports:**
   - Page views and screens
   - User engagement metrics
   - GA4 → Reports → Engagement

3. **Conversion Reports:**
   - Subscription completions
   - Revenue tracking
   - GA4 → Reports → Monetization

4. **User Acquisition:**
   - Where users come from
   - Campaign performance
   - GA4 → Reports → Acquisition

5. **Custom Reports:**
   - Create custom reports
   - GA4 → Explore → Create new exploration

---

## 🎯 Optional Analytics Tools

### PostHog (Recommended for Product Analytics)

**Features:**
- Session recordings (watch user interactions)
- Heatmaps
- Feature flags
- Advanced funnel analysis
- User cohorts

**Setup:**

1. Sign up at [https://posthog.com](https://posthog.com) (Free tier: 1M events/month)

2. Create a new project

3. Get your Project API Key

4. Add to `.env.local`:
   ```bash
   NEXT_PUBLIC_POSTHOG_KEY=phc_xxxxxxxxxxxxxxxxxxxxxxxx
   NEXT_PUBLIC_POSTHOG_HOST=https://app.posthog.com
   ```

5. For production, add to environment variables

**Benefits:**
- See exactly how users navigate your app
- Identify UX issues with session recordings
- Track feature adoption
- Run A/B tests

---

### Plausible (Privacy-Friendly Alternative)

**Features:**
- GDPR compliant
- No cookies
- Lightweight (< 1KB)
- Simple, beautiful dashboard

**Setup:**

1. Sign up at [https://plausible.io](https://plausible.io) ($9/month)

2. Add your domain: `bonidoc.com`

3. Add to `.env.local`:
   ```bash
   NEXT_PUBLIC_PLAUSIBLE_DOMAIN=bonidoc.com
   ```

4. For production, add to environment variables

**Benefits:**
- No cookie banner needed
- Privacy-first analytics
- Public dashboard option
- EU-based servers

---

## 🔍 Debugging Analytics

### Check if Analytics is Loading:

1. **Open Browser DevTools** (F12)
2. **Console Tab** - Look for:
   ```
   [Analytics DEV] Pageview: /dashboard
   [Analytics DEV] Event: { action: 'document_upload', category: 'documents', ... }
   ```

3. **Network Tab:**
   - Filter by "gtag" or "google-analytics"
   - Should see requests to `google-analytics.com`

### Common Issues:

**❌ Analytics not tracking:**
- Check `.env.local` has `NEXT_PUBLIC_GA_MEASUREMENT_ID=G-4ZJWP2FWRZ`
- Restart development server after changing env vars
- Clear browser cache
- Check browser has "Do Not Track" disabled

**❌ Events not appearing in GA4:**
- Events can take 5-30 seconds to appear in Real-Time
- Historical reports can take 24-48 hours to update
- Check event name matches exactly (case-sensitive)

**❌ Development events polluting production data:**
- In GA4, create a filter to exclude localhost traffic:
  - Admin → Data Settings → Data Filters
  - Create filter: Exclude hostname contains "localhost"

---

## 📱 Mobile App Analytics

If you build a mobile app in the future, GA4 supports:
- iOS (Swift)
- Android (Kotlin)
- React Native
- Flutter

Same Measurement ID (G-4ZJWP2FWRZ) can track web + mobile.

---

## 🎓 Best Practices

1. **Track User Journey:**
   - Login → Dashboard → Upload → Categorize → Search
   - Identify drop-off points

2. **Set Up Funnels:**
   - Landing Page → Signup → Subscribe → First Upload
   - Track conversion rate at each step

3. **Monitor Key Metrics:**
   - Daily Active Users (DAU)
   - Monthly Active Users (MAU)
   - Subscription conversion rate
   - Average documents per user
   - Delegate invitation acceptance rate

4. **A/B Testing:**
   - Use PostHog feature flags
   - Test pricing changes
   - Test UI variations
   - Measure impact on conversions

5. **Privacy Compliance:**
   - Analytics respects "Do Not Track"
   - IP addresses anonymized
   - GDPR-compliant with PostHog in EU mode

---

## 🆘 Support

- **Google Analytics Help:** [https://support.google.com/analytics](https://support.google.com/analytics)
- **PostHog Docs:** [https://posthog.com/docs](https://posthog.com/docs)
- **Plausible Docs:** [https://plausible.io/docs](https://plausible.io/docs)

---

## ✅ Quick Start Checklist

- [x] Google Analytics 4 configured (G-4ZJWP2FWRZ)
- [x] Analytics code installed in app
- [x] Development testing enabled
- [ ] Configure enhanced measurement in GA4
- [ ] Set up conversion events in GA4
- [ ] Test analytics in development (open console, perform actions)
- [ ] View real-time reports in GA4
- [ ] (Optional) Sign up for PostHog for session recordings
- [ ] (Optional) Sign up for Plausible for privacy-friendly analytics
- [ ] Deploy to production with environment variables

---

---

## 🎯 Immediate Action Checklist (Do This Now!)

### Today (30 minutes):

- [ ] **Step 1:** Open [Google Analytics](https://analytics.google.com) and log in
- [ ] **Step 2:** Go to Admin → Data Streams → Click bonidoc.com stream
- [ ] **Step 3:** Enable Enhanced Measurement (all toggles ON)
- [ ] **Step 4:** Enable Debug Mode (in Additional Settings)
- [ ] **Step 5:** Start your dev server (`cd frontend && npm run dev`)
- [ ] **Step 6:** Open browser console (F12), navigate to http://localhost:3000
- [ ] **Step 7:** Look for `[Analytics DEV]` logs in console
- [ ] **Step 8:** In GA4, go to Reports → Realtime → See your pageview appear!

### This Week:

- [ ] **Mark conversions:** Admin → Events → Toggle "Mark as conversion" for `purchase`, `signup`, `login`
- [ ] **Create funnel:** Explore → Funnel exploration → Add signup → subscription → purchase steps
- [ ] **Set up custom dimensions:** Admin → Custom definitions → Add User Tier, Document Type, Billing Cycle
- [ ] **Create audiences:** Admin → Audiences → Add "Engaged Free Users" and "Cart Abandoners"
- [ ] **Exclude localhost:** Admin → Data Filters → Add filter for localhost

### Later (Optional):

- [ ] Sign up for PostHog (session recordings)
- [ ] Link Google Ads account
- [ ] Set up BigQuery export
- [ ] Create custom dashboards

---

## 🚨 Troubleshooting Guide

### Problem: "I don't see any events in Google Analytics"

**Solution:**

1. **Check Real-Time Reports (not historical)**
   - Go to Reports → Realtime (not Overview)
   - Historical reports take 24-48 hours to update

2. **Verify environment variable:**
   ```bash
   cd frontend
   cat .env.local | grep GA_MEASUREMENT_ID
   # Should show: NEXT_PUBLIC_GA_MEASUREMENT_ID=G-4ZJWP2FWRZ
   ```

3. **Restart dev server:**
   ```bash
   # Kill current server (Ctrl+C)
   npm run dev
   ```

4. **Check browser console:**
   - Open DevTools (F12)
   - Should see: `[Analytics DEV] Pageview: /dashboard`
   - If not, check `.env.local` has `NEXT_PUBLIC_ENABLE_ANALYTICS_DEV=true`

5. **Clear browser cache:**
   - Chrome: Ctrl+Shift+Delete → Clear cached images and files

---

### Problem: "Events show in console but not in GA4"

**Solution:**

1. **Check Network tab in DevTools:**
   - Filter by "gtag"
   - Should see requests to `https://www.google-analytics.com/g/collect`
   - If RED (failed), check internet connection

2. **Wait 30 seconds:**
   - GA4 real-time has ~10-30 second delay
   - Refresh the Realtime report page

3. **Check ad blockers:**
   - Disable uBlock Origin, AdBlock, etc.
   - They block GA4 tracking scripts

4. **Verify measurement ID:**
   - In Network tab, check request URL contains `G-4ZJWP2FWRZ`
   - If different ID, update `.env.local`

---

### Problem: "Revenue not showing in reports"

**Solution:**

1. **Verify ecommerce setup:**
   - Admin → Data display → Toggle ON "Show advanced metrics"
   - Admin → Events → Mark `purchase` as conversion

2. **Check purchase event format:**
   - Events must include `value`, `currency`, and `transaction_id`
   - Our code already does this correctly

3. **Wait for data:**
   - Revenue reports update daily
   - Real-time shows events, but revenue appears in Monetization reports later

4. **Test with Stripe test mode:**
   - Complete a test subscription
   - Check DebugView → Should see `purchase` event with value

---

### Problem: "DebugView is empty"

**Solution:**

1. **Enable Debug Mode:**
   - Admin → Data Streams → Your stream
   - Additional Settings → Configure tag settings
   - Debug mode → Toggle ON

2. **Install Google Analytics Debugger:**
   - [Chrome Extension](https://chrome.google.com/webstore/detail/google-analytics-debugger/jnkmfdileelhofjcijamephohjechhna)
   - Click extension icon (should turn blue)
   - Reload page

3. **Check DebugView in GA4:**
   - Admin → DebugView (left sidebar)
   - Select your device from dropdown
   - Should see events within 5 seconds

---

### Problem: "Too many events from localhost in production reports"

**Solution:**

1. **Create data filter:**
   - Admin → Data Settings → Data Filters
   - Create filter: Exclude `page_location` contains `localhost`
   - Set to Active

2. **Use separate GA4 property for dev:**
   - Create new GA4 property "BoniDoc Development"
   - Use different measurement ID in `.env.local`
   - Keep production ID in production env vars only

---

### Problem: "Custom events not appearing"

**Solution:**

1. **Don't create events in GA4 console - they're already in code!**
   - Our code sends: `signup`, `login`, `document_upload`, etc.
   - Just wait for events to appear (24-48 hours max)
   - Then mark as conversions

2. **If you created custom events by mistake:**
   - Admin → Events → Find the event
   - Click three dots → Delete
   - Let the code-based events populate naturally

---

## 📊 Key Reports to Monitor

### Daily:
- **Realtime** → See active users right now
- **Realtime → Event count by Event name** → See which features are being used

### Weekly:
- **Acquisition → User acquisition** → Where users come from
- **Engagement → Events** → Most popular actions
- **Monetization → Overview** → Revenue trends

### Monthly:
- **Engagement → Conversions** → Conversion trends over time
- **Explore → Funnel** → Signup → Subscription conversion rate
- **Explore → Path exploration** → How users navigate your app

---

## 🎓 Pro Tips

### 1. Use DebugView for Real-Time Testing

Instead of waiting for reports:
1. Install GA Debugger extension
2. Open DebugView in GA4
3. Perform actions in your app
4. See events appear instantly in DebugView

### 2. Create Comparison Reports

Compare different time periods:
1. Any report → Date range dropdown
2. Click "Compare" checkbox
3. Select "Previous period" or "Previous year"
4. See growth/decline trends instantly

### 3. Set Up Alerts

Get notified when important things happen:
1. Go to Admin → Custom insights
2. Create alert: "Daily users drops 50%"
3. Get email when traffic drops significantly

### 4. Export Data Regularly

Back up your analytics:
1. Any report → Share icon → Download CSV
2. Or set up BigQuery automatic export
3. Never lose historical data

### 5. Test Before Launch

Before production launch:
1. Complete a full user journey (signup → subscribe → upload)
2. Check each event fires in DebugView
3. Verify revenue value is correct
4. Test on mobile and desktop

---

## ✅ Success Metrics to Track

### Week 1:
- **Goal:** See events flowing in
- **Check:** Realtime report shows your activity
- **Metric:** > 0 events recorded

### Week 2:
- **Goal:** First conversions tracked
- **Check:** Monetization report shows revenue
- **Metric:** > 0 subscriptions

### Month 1:
- **Goal:** Understand user journey
- **Check:** Funnel report shows drop-off points
- **Metric:** Identify where users abandon signup flow

### Month 3:
- **Goal:** Optimize conversion rate
- **Check:** Compare this month vs last month
- **Metric:** Increase signup → subscription conversion by 10%

### Month 6:
- **Goal:** ROI positive on Google Ads
- **Check:** Cost per acquisition < Lifetime value
- **Metric:** CAC < $50, LTV > $200

---

## 📚 Learning Resources

### Google Analytics Academy (Free):
- [GA4 Beginner Course](https://analytics.google.com/analytics/academy/)
- [GA4 Advanced Course](https://analytics.google.com/analytics/academy/)
- [Ecommerce Analytics](https://analytics.google.com/analytics/academy/)

### YouTube Channels:
- [Measure School](https://www.youtube.com/c/MeasureSchool) - GA4 tutorials
- [Analytics Mania](https://www.youtube.com/c/AnalyticsMania) - Advanced tracking

### Communities:
- [r/GoogleAnalytics](https://reddit.com/r/GoogleAnalytics)
- [Measure Slack](https://www.measure.chat/)

---

**Analytics is now live and tracking! 🎉**

**Next step:** Open your app, perform some actions, then check GA4 Real-Time reports to see events flowing in.

**Questions?** Check the troubleshooting section above or the [GA4 Help Center](https://support.google.com/analytics).
