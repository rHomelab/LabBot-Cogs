# Onboarding Role Cog - Diagnostic Testing Guide

## Changes Made

This branch includes diagnostic improvements to help identify why the onboarding role assignment is not working. NO FUNCTION HAS ACTUALLY CHANGED

## Note
I (naro) had to change the create dev bot shell for my local environment. the provided one was not working. 

### 1. New Diagnostic Command: `checkflag`

A new command has been added to test if the bot can access the `completed_onboarding` flag:

```
[p]onboarding_role checkflag [@member]
```

**What it does:**
- Checks if the `flags` attribute exists on member objects
- Checks if the `completed_onboarding` flag is accessible
- Shows the current value of the flag for the specified member
- Lists all available member flags
- Displays the discord.py version
- Shows member information (ID, bot status, join date)

**Usage:**
- `[p]onboarding_role checkflag` - Check your own flags
- `[p]onboarding_role checkflag @SomeUser` - Check another user's flags

### 2. Enhanced Logging

The `on_member_update` listener now includes:
- **Error handling** for `AttributeError` when accessing the `completed_onboarding` flag
- **Debug logging** when the onboarding flag changes for any user
- **Info logging** when a user completes onboarding and role assignment is triggered
- **Detailed error messages** if the flag cannot be accessed

## Testing Steps

### Step 1: Check Discord.py Version and Flag Support

Run the diagnostic command on yourself or a test user:
```
[p]onboarding_role checkflag
```

**Expected Results:**
- ✅ **If working correctly:** You should see "Has 'completed_onboarding' flag: ✅ Yes"
- ❌ **If broken:** You'll see "Has 'completed_onboarding' flag: ❌ No"

### Step 2: Check a User Who Has Completed Onboarding

Run the command on a user who you know has completed onboarding:
```
[p]onboarding_role checkflag @UserWhoCompletedOnboarding
```

**Expected Results:**
- The "Completed Onboarding Flag Value" should show "✅ True"
- If it shows "❌ False", the user hasn't completed onboarding (or the flag isn't working)

### Step 3: Monitor Logs During Onboarding

Set the bot's log level to DEBUG (if possible) and watch the logs when a new user completes onboarding.

**What to look for:**
- `Onboarding flag changed for 'Username' (ID 123): False -> True` - This means the flag change was detected
- `User 'Username' (ID 123) just completed onboarding, processing role assignment...` - This means the role assignment is being triggered
- `Failed to access completed_onboarding flag` - This means the flag isn't accessible (likely the root cause)

### Step 4: Test Manual Processing

Try manually processing onboarding for all members:
```
[p]onboarding_role process True
```

This will do a dry run and tell you how many members would be processed. If it returns 0 but you know there are users who completed onboarding without the role, the flag isn't working.

## Common Issues and Solutions

### Issue 1: Flag Not Accessible
**Symptom:** `checkflag` shows "Has 'completed_onboarding' flag: ❌ No"

**Possible Causes:**
1. **Discord.py version too old** - The `completed_onboarding` flag was added in discord.py 2.0+
2. **Missing intents** - The bot needs `GUILD_MEMBERS` intent enabled
3. **Red-DiscordBot version** - May need to update Red-DiscordBot

**Solutions:**
- Check discord.py version: Should be 2.0 or higher
- Verify bot intents in Discord Developer Portal: Enable "Server Members Intent"
- Update Red-DiscordBot: `pip install -U Red-DiscordBot`

### Issue 2: Flag Exists But Always Shows False
**Symptom:** `checkflag` shows the flag exists, but it's always False even for users who completed onboarding

**Possible Causes:**
1. **Cache not populated** - The bot's member cache might not be up to date
2. **Intent not enabled** - Even if the flag exists, without proper intents it won't be populated
3. **Discord API issue** - Discord might not be sending the flag data

**Solutions:**
- Restart the bot to refresh the cache
- Double-check "Server Members Intent" is enabled in Discord Developer Portal
- Try `[p]onboarding_role process` to force a check of all members

### Issue 3: Flag Works But Role Not Assigned
**Symptom:** `checkflag` shows True for completed onboarding, but role isn't assigned

**Possible Causes:**
1. **Permission issue** - Bot can't assign the role
2. **Role hierarchy** - The onboarding role is higher than the bot's role
3. **Role not configured** - The onboarding role isn't set in the cog

**Solutions:**
- Check bot permissions: Needs "Manage Roles" permission
- Check role hierarchy: Bot's highest role must be above the onboarding role
- Verify configuration: `[p]onboarding_role status`

## Next Steps Based on Results

### If the flag is NOT accessible:
This is the root cause. The bot cannot detect when users complete onboarding. You need to:
1. Update discord.py to version 2.0+
2. Enable "Server Members Intent" in Discord Developer Portal
3. Update Red-DiscordBot if needed

### If the flag IS accessible but always False:
The flag exists but isn't being populated. You need to:
1. Enable "Server Members Intent" in Discord Developer Portal
2. Restart the bot
3. Check if Discord's onboarding feature is properly configured in server settings

### If the flag works but roles aren't assigned:
The detection is working but assignment is failing. Check:
1. Bot permissions (Manage Roles)
2. Role hierarchy (bot role must be higher)
3. Check logs for "Forbidden" errors

## Additional Information

### Required Bot Intents
The bot needs these intents enabled in the Discord Developer Portal:
- ✅ Server Members Intent (required for member flag updates)
- ✅ Message Content Intent (for commands)

### Required Bot Permissions
The bot needs these permissions in the server:
- ✅ Manage Roles
- ✅ Send Messages
- ✅ Embed Links (for status/diagnostic messages)

### Discord.py Version Requirements
- Minimum version: 2.0.0 (for `completed_onboarding` flag support)
- Recommended: Latest stable version

## Contact

If you continue to have issues after following this guide, please provide:
1. Output of `[p]onboarding_role checkflag`
2. Discord.py version (shown in checkflag output)
3. Any error messages from the bot logs
4. Screenshot of bot intents in Discord Developer Portal
