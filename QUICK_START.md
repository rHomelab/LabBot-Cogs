# Quick Start - Testing Onboarding Role Cog

## 🚀 Fast Setup (5 minutes)

### 1. Start the Dev Bot
```bash
cd /Users/dustin/local-repos/LabBot-Cogs
./create_dev_bot_py311.sh
# Enter your bot token and prefix when prompted
# Note: Uses Python 3.11 (Red-DiscordBot requires Python 3.8-3.11)
```

### 2. Run the Bot
```bash
source .venv/bin/activate
redbot RedBot_dev_homelab
```

### 3. Configure in Discord
```
!addpath /Users/dustin/local-repos/LabBot-Cogs
!load onboarding_role
!onboarding_role role @YourRole
!onboarding_role logchannel #logs
```

### 4. Run Diagnostic
```
!onboarding_role checkflag
```

## 🔍 What to Look For

### ✅ Good Result:
```
Has 'flags' attribute: ✅ Yes
Has 'completed_onboarding' flag: ✅ Yes
Discord.py Version: 2.x.x
```
→ **The flag is accessible! Test with a real user completing onboarding.**

### ❌ Bad Result:
```
Has 'completed_onboarding' flag: ❌ No
```
→ **Problem found! Check:**
1. Discord.py version (needs 2.0+)
2. Server Members Intent enabled in Discord Developer Portal
3. Bot restarted after enabling intents

## 🛠️ Critical Bot Settings

**Discord Developer Portal** (https://discord.com/developers/applications):
- Bot → Privileged Gateway Intents
  - ✅ **SERVER MEMBERS INTENT** (REQUIRED!)
  - ✅ **MESSAGE CONTENT INTENT** (REQUIRED!)

**Bot Permissions in Server:**
- ✅ Manage Roles
- ✅ Send Messages
- ✅ Embed Links

**Role Hierarchy:**
- Bot's role must be **above** the onboarding role in Server Settings → Roles

## 📊 Test Commands

```bash
# Check if flag works
!onboarding_role checkflag

# Check another user
!onboarding_role checkflag @User

# See configuration
!onboarding_role status

# Dry run (see who would be processed)
!onboarding_role process True

# Actually process all members
!onboarding_role process

# Reload after code changes
!reload onboarding_role

# Enable debug logging
!set loglevel debug
```

## 🐛 Common Issues

| Issue | Solution |
|-------|----------|
| Flag doesn't exist | Enable Server Members Intent in Developer Portal, restart bot |
| Flag always False | Wait 2-3 minutes for cache, or restart bot |
| Role not assigned | Check bot has "Manage Roles" permission and role hierarchy |
| No logs when onboarding | Server Members Intent not enabled |

## 📖 Full Documentation

- **LOCAL_TESTING_GUIDE.md** - Complete step-by-step testing guide
- **onboarding_role/DIAGNOSTIC_TESTING.md** - Detailed troubleshooting

## 🎯 Expected Behavior

When a user completes onboarding, you should see in bot console:
```
[INFO] User 'Username' (ID 123) just completed onboarding, processing role assignment...
[INFO] User 'Username' (ID 123) completed onboarding and was added to the onboarding role.
```

And in your log channel (if configured):
```
User Completed Onboarding
Member: @Username
Time to Completion: 2 minutes, 30 seconds
User added to onboarding role.
```
