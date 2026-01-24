# 🔧 Setup Guide

This guide walks you through setting up the MyWhoosh2Garmin automation from scratch.

## Prerequisites

Before you begin, make sure you have:

- ✅ A GitHub account (for running GitHub Actions)
- ✅ A Strava account with MyWhoosh auto-upload enabled
- ✅ A Garmin Connect account
- ✅ Python 3.13+ installed locally (for initial setup only)

## Step 1: Fork the Repository

1. Click the **Fork** button at the top of this repository
2. Clone your fork to your local machine:
   ```bash
   git clone https://github.com/YourUsername/MyWhoosh2Garmin.git
   cd MyWhoosh2Garmin
   ```

## Step 2: Local Environment Setup

Install dependencies using `uv` (recommended) or `pip`:

```bash
# Install uv package manager
pip install uv

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# OR
.venv\Scripts\activate      # On Windows

# Install dependencies
uv pip install -r pyproject.toml
```

## Step 3: Strava API Application

1. Go to [Strava API Settings](https://www.strava.com/settings/api)
2. Create a new application with these settings:
   - **Application Name**: MyWhoosh2Garmin (or your choice)
   - **Category**: Training
   - **Club**: Leave empty
   - **Website**: Your GitHub repo URL
   - **Authorization Callback Domain**: `localhost`
3. Note your **Client ID** and **Client Secret**

## Step 4: Authenticate with Strava

Run the Strava setup script:

```bash
python setup_strava_auth.py
```

Follow the prompts:
1. Enter your **Client ID** and **Client Secret**
2. Open the authorization URL in your browser
3. Click **Authorize**
4. Copy the full callback URL from your browser (it will look like `http://localhost/exchange_token?code=...`)
5. Paste it back into the terminal

The script will output all the GitHub Secrets you need. **Keep this window open** — you'll need these values in Step 6.

## Step 5: Authenticate with Garmin

Run the Garmin setup script:

```bash
python setup_garmin_auth.py
```

Follow the prompts:
1. Enter your Garmin email address
2. Enter your Garmin password
3. If you have 2FA enabled, enter the code when prompted

The script will output the `GARMIN_TOKENS` secret. **Copy this** — you'll need it in Step 6.

## Step 6: Configure GitHub Secrets

Now add all the secrets to your GitHub repository:

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** for each of the following:

### From Strava Setup Script

| Secret Name | Value |
|-------------|-------|
| `STRAVA_CLIENT_ID` | Your Strava Client ID |
| `STRAVA_CLIENT_SECRET` | Your Strava Client Secret |
| `STRAVA_ACCESS_TOKEN` | From script output |
| `STRAVA_EXPIRES_AT` | From script output |
| `STRAVA_EXPIRES_IN` | From script output |
| `STRAVA_REFRESH_TOKEN` | From script output |

### From Garmin Setup Script

| Secret Name | Value |
|-------------|-------|
| `GARMIN_TOKENS` | The full token string from script output |

## Step 7: Test the Workflow

1. Go to **Actions** tab in your repository
2. Click **Self-hosted runner — Run MyWhoosh2Garmin**
3. Click **Run workflow** → **Run workflow**

The workflow will:
- ✅ Check your recent Garmin activities
- ✅ Fetch MyWhoosh activities from Strava
- ✅ Upload any new activities to Garmin Connect

Check the workflow logs to verify everything worked!

## Step 8: Optional - Set Up Webhook for Instant Sync

For automatic sync immediately after uploading to Strava, you can set up a webhook using my [WebhookProcessor](https://github.com/MarcChen/WebhookProcessor):

### Quick Setup

1. Deploy WebhookProcessor to your preferred cloud platform (Vercel, Cloudflare Workers, etc.)
2. Set up the webhook to trigger your GitHub Actions workflow
3. Configure Strava webhook subscription:
   ```bash
   # Create webhook subscription
   curl -X POST https://www.strava.com/api/v3/push_subscriptions \
     -F client_id=YOUR_CLIENT_ID \
     -F client_secret=YOUR_CLIENT_SECRET \
     -F callback_url=YOUR_WEBHOOK_URL \
     -F verify_token=RANDOM_STRING
   ```

See [WebhookProcessor documentation](https://github.com/MarcChen/WebhookProcessor) for detailed instructions.

## Troubleshooting

### Token Expiration

Strava tokens automatically refresh when expired. If you see authentication errors:
1. Re-run `setup_strava_auth.py`
2. Update the GitHub Secrets with new values

### Garmin Authentication Failed

If Garmin authentication fails:
1. Check your username/password are correct
2. If you have 2FA, make sure you're entering the code quickly
3. Re-run `setup_garmin_auth.py` and update `GARMIN_TOKENS` secret

### No Activities Found

Make sure:
- Your MyWhoosh activities are uploaded to Strava
- Activity names contain "MyWhoosh"
- Activity type is set to "Virtual Ride"
- You ran a ride within the last 7 days

### Workflow Fails

Check the workflow logs in the Actions tab for specific error messages. Common issues:
- Missing or incorrect GitHub Secrets
- Token expiration (re-authenticate and update secrets)
- Network connectivity issues (re-run the workflow)

## Security Best Practices

- 🔒 **Never commit** `.env` or `strava_tokens.json` to version control (they're gitignored)
- 🔒 **Never share** your GitHub Secrets publicly
- 🔒 **Rotate tokens** periodically for better security
- 🔒 **Use 2FA** on both Strava and Garmin accounts

## Next Steps

Once everything is working:
- Set up a webhook for instant sync (Step 8)
- Customize the workflow schedule in `.github/workflows/self-hosted-runner.yml`
- Star this repo if you find it useful! ⭐
