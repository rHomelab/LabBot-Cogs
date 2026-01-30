# Local Testing Guide for Onboarding Role Cog

This guide will help you test the onboarding_role cog changes locally using the dev bot setup.

## Prerequisites

- Python 3.8 or higher installed
- A Discord bot token (from Discord Developer Portal)
- A test Discord server where you have admin permissions
- Discord bot with the following settings in Developer Portal:
  - ✅ **Server Members Intent** enabled (critical!)
  - ✅ **Message Content Intent** enabled
  - ✅ Bot invited to your test server with "Manage Roles" permission

## Step 1: Set Up the Dev Bot

### 1.1 Navigate to the Repository
```bash
cd /Users/dustin/local-repos/LabBot-Cogs
```

### 1.2 Run the Dev Bot Setup Script
```bash
./create_dev_bot.sh
```

**You'll be prompted for:**
- **Bot Token**: Paste your Discord bot token from the Developer Portal
- **Bot Prefix**: Enter a prefix (default is `!`, you can use something like `?` or `dev!`)

**What this does:**
- Creates a Python virtual environment (`.venv`)
- Installs all required dependencies
- Sets up a Red-DiscordBot instance named `RedBot_dev_homelab`
- Configures the bot with your token and prefix

### 1.3 Start the Bot
```bash
source .venv/bin/activate  # Activate the virtual environment
redbot RedBot_dev_homelab
```

The bot should now start and connect to Discord!

## Step 2: Configure the Bot

### 2.1 Add the Cog Path

In your test Discord server, send this command:
```
!addpath /Users/dustin/local-repos/LabBot-Cogs
```
*(Replace `!` with your chosen prefix)*

The bot will respond confirming the path was added.

### 2.2 Load the Onboarding Role Cog
```
!load onboarding_role
```

The bot should respond with a checkmark ✅ indicating the cog loaded successfully.

### 2.3 Configure the Cog

**Set the onboarding role:**
```
!onboarding_role role @YourRoleName
```
Or use the role ID:
```
!onboarding_role role 1234567890123456789
```

**Set a log channel (optional but recommended):**
```
!onboarding_role logchannel #bot-logs
```

**Check the configuration:**
```
!onboarding_role status
```

## Step 3: Run Diagnostics

### 3.1 Check if the Flag is Accessible

Run the new diagnostic command on yourself:
```
!onboarding_role checkflag
```

**What to look for:**
- ✅ **"Has 'flags' attribute: ✅ Yes"** - Good!
- ✅ **"Has 'completed_onboarding' flag: ✅ Yes"** - Perfect! The flag is accessible
- ❌ **"Has 'completed_onboarding' flag: ❌ No"** - Problem! See troubleshooting below
- Check the **Discord.py Version** - Should be 2.0 or higher

### 3.2 Check a Test User

If you have another account or a friend in the test server:
```
!onboarding_role checkflag @TestUser
```

This will show if the flag is True (completed onboarding) or False (not completed).

### 3.3 Check Bot Logs

Watch the bot's console output for log messages. You should see:
- Debug messages when member updates occur
- Info messages when onboarding is completed
- Error messages if the flag cannot be accessed

## Step 4: Test the Onboarding Flow

### 4.1 Set Up Discord Server Onboarding

In your test Discord server:
1. Go to **Server Settings** → **Onboarding**
2. Enable onboarding if not already enabled
3. Configure at least one onboarding question/step
4. Save the onboarding setup

### 4.2 Test with a New Account

**Option A: Use an Alt Account**
1. Join the test server with an alt Discord account
2. Complete the onboarding flow
3. Watch the bot logs for messages like:
   ```
   Onboarding flag changed for 'Username' (ID 123): False -> True
   User 'Username' (ID 123) just completed onboarding, processing role assignment...
   ```
4. Check if the role was assigned

**Option B: Test with Existing Members**
```
!onboarding_role process True
```
This does a dry run showing how many members would be processed.

Then run without dry run:
```
!onboarding_role process
```

## Step 5: Troubleshooting

### Issue: "Has 'completed_onboarding' flag: ❌ No"

**Cause:** Discord.py version doesn't support the flag, or intents are missing.

**Solutions:**

1. **Check Discord.py version:**
   ```bash
   source .venv/bin/activate
   pip show discord.py
   ```
   Should be version 2.0 or higher.

2. **Update discord.py if needed:**
   ```bash
   pip install -U discord.py
   ```

3. **Verify bot intents in Discord Developer Portal:**
   - Go to https://discord.com/developers/applications
   - Select your bot application
   - Go to **Bot** section
   - Scroll to **Privileged Gateway Intents**
   - Enable **"SERVER MEMBERS INTENT"** ✅ (This is critical!)
   - Enable **"MESSAGE CONTENT INTENT"** ✅
   - Save changes
   - Restart the bot

### Issue: Flag Exists But Always Shows False

**Cause:** Bot intents not enabled or cache not populated.

**Solutions:**

1. **Double-check intents are enabled** (see above)
2. **Restart the bot:**
   - Press `Ctrl+C` in the terminal running the bot
   - Run `redbot RedBot_dev_homelab` again
3. **Wait a few minutes** for the cache to populate
4. **Try the checkflag command again**

### Issue: Flag Shows True But Role Not Assigned

**Cause:** Permission or role hierarchy issue.

**Solutions:**

1. **Check bot permissions:**
   - Bot needs "Manage Roles" permission
   - Check with: Right-click bot → View Roles

2. **Check role hierarchy:**
   - In Server Settings → Roles
   - The bot's highest role must be **above** the onboarding role
   - Drag the bot's role higher if needed

3. **Check the logs:**
   - Look for "Forbidden" errors in the bot console
   - These indicate permission issues

### Issue: Bot Not Detecting Onboarding Completion

**Cause:** `on_member_update` event not firing.

**Solutions:**

1. **Verify Server Members Intent is enabled** (most common cause)
2. **Check if onboarding is properly configured** in server settings
3. **Look for AttributeError in logs** - indicates flag access issues

## Step 6: Viewing Logs

### Enable Debug Logging

To see more detailed logs:
```
!set loglevel debug
```

This will show all debug messages including:
- When the onboarding flag changes
- When role assignment is triggered
- Detailed error messages

### Disable Debug Logging

When you're done testing:
```
!set loglevel info
```

## Step 7: Making Changes and Reloading

If you need to make code changes:

1. **Edit the code** in your editor
2. **Reload the cog** without restarting the bot:
   ```
   !reload onboarding_role
   ```
3. **Test again**

## Step 8: Stopping the Bot

When you're done testing:
1. Press `Ctrl+C` in the terminal running the bot
2. Deactivate the virtual environment:
   ```bash
   deactivate
   ```

## Quick Reference Commands

```bash
# Start the bot
source .venv/bin/activate
redbot RedBot_dev_homelab

# In Discord:
!addpath /Users/dustin/local-repos/LabBot-Cogs
!load onboarding_role
!onboarding_role role @RoleName
!onboarding_role logchannel #logs
!onboarding_role status
!onboarding_role checkflag
!onboarding_role checkflag @User
!onboarding_role process True  # Dry run
!onboarding_role process       # Actually process
!reload onboarding_role        # After code changes
```

## Expected Results

### ✅ If Everything Works:

1. `checkflag` shows the flag exists and is accessible
2. When a user completes onboarding, you see in logs:
   ```
   Onboarding flag changed for 'Username': False -> True
   User 'Username' just completed onboarding, processing role assignment...
   User 'Username' completed onboarding and was added to the onboarding role.
   ```
3. The role is automatically assigned
4. A message appears in the log channel (if configured)

### ❌ If It Doesn't Work:

1. `checkflag` shows the flag doesn't exist → **Discord.py version or intents issue**
2. Flag exists but always False → **Intents not enabled or cache issue**
3. Flag works but no role assigned → **Permissions or role hierarchy issue**
4. No logs appear when onboarding completes → **Server Members Intent not enabled**

## Getting Help

If you're still having issues after following this guide, collect the following information:

1. Output of `!onboarding_role checkflag`
2. Output of `!onboarding_role status`
3. Discord.py version (shown in checkflag output)
4. Screenshot of bot intents in Discord Developer Portal
5. Any error messages from the bot console
6. Bot console logs when a user completes onboarding

See `onboarding_role/DIAGNOSTIC_TESTING.md` for more detailed troubleshooting information.
