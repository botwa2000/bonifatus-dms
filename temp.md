# Facebook Login Setup Guide (DEV)

Step-by-step guide to configure Facebook Login on developers.facebook.com for the DEV environment.

---

## Step 1: Go to Facebook Developers

1. Open https://developers.facebook.com/
2. Log in with your Facebook account
3. Click **"My Apps"** in the top right

## Step 2: Create a New App

1. Click **"Create App"**
2. Select **"Other"** as the use case, click **Next**
3. Select **"Consumer"** as the app type, click **Next**
4. Fill in:
   - **App Name:** `BoniDoc DEV`
   - **App Contact Email:** your email
5. Click **"Create App"**

## Step 3: Add Facebook Login Product

1. From the app dashboard, find **"Facebook Login"** in the product list
2. Click **"Set Up"**
3. Select **"Web"** as the platform
4. For **Site URL**, enter: `https://dev.bonidoc.com`
5. Click **"Save"** then **"Continue"** through the remaining quickstart steps (you can skip them)

## Step 4: Configure OAuth Settings

1. In the left sidebar, go to **Facebook Login > Settings**
2. Configure these settings:

| Setting | Value |
|---------|-------|
| **Client OAuth Login** | ON |
| **Web OAuth Login** | ON |
| **Enforce HTTPS** | ON |
| **Embedded Browser OAuth Login** | OFF |
| **Login from Devices** | OFF |
| **Valid OAuth Redirect URIs** | `https://api-dev.bonidoc.com/api/v1/auth/facebook/callback` |

3. Click **"Save Changes"**

## Step 5: Configure App Settings

1. In the left sidebar, go to **Settings > Basic**
2. Verify:
   - **App ID** matches: `1440613847708620`
   - **App Secret** matches what you provided (click "Show" to verify)
3. Fill in required fields:
   - **Privacy Policy URL:** `https://dev.bonidoc.com/legal/privacy`
   - **Terms of Service URL:** `https://dev.bonidoc.com/legal/terms`
   - **App Icon:** Upload one of the logo files from `assets/` folder
   - **Category:** Select "Business" or "Utilities"
4. Click **"Save Changes"**

## Step 6: Configure Data Deletion

1. In the left sidebar, go to **Settings > Basic**
2. Scroll down to **"Data Deletion"** section
3. Select **"Data Deletion Callback URL"**
4. Enter: `https://api-dev.bonidoc.com/api/v1/auth/facebook/data-deletion`
5. Click **"Save Changes"**

## Step 7: Set Permissions

1. In the left sidebar, go to **App Review > Permissions and Features**
2. Verify these permissions are listed:
   - `email` - should be available by default
   - `public_profile` - should be available by default
3. No additional permissions need to be requested for DEV mode

## Step 8: Keep App in Development Mode

- The app is in **Development Mode** by default
- This means only app admins and testers can log in
- This is perfect for DEV testing
- Do NOT switch to Live Mode yet (that requires App Review for PROD)

## Step 9: Add Test Users (Optional)

1. In the left sidebar, go to **App Roles > Roles**
2. You can add testers here who can test the login flow
3. Click **"Add People"** and enter their Facebook email

## Step 10: Test the Flow

1. Open https://dev.bonidoc.com/login
2. You should see the **"Sign in with Facebook"** button
3. Click it - you should be redirected to Facebook's OAuth dialog
4. Authorize the app
5. You should be redirected back to the dashboard
6. Check the database: the user should have `facebook_id` populated

---

## Troubleshooting

- **"App not set up" error:** Make sure the Valid OAuth Redirect URI is exactly `https://api-dev.bonidoc.com/api/v1/auth/facebook/callback`
- **No email returned:** The user's Facebook account must have a verified email address
- **"Developer Only" warning:** This is normal in Development Mode - only admins/testers can log in
- **Redirect loop:** Check that `FACEBOOK_REDIRECT_URI` env var matches what's configured in Facebook

---

## For PROD Later

When ready for production:
1. Create a separate Facebook app (or switch this one to Live)
2. Set redirect URI to `https://api.bonidoc.com/api/v1/auth/facebook/callback`
3. Submit for **App Review** requesting `email` and `public_profile` permissions
4. Provide a screencast of the login flow
5. Create Docker secrets: `facebook_client_id_prod` and `facebook_client_secret_prod`
6. Switch to **Live Mode** after approval
