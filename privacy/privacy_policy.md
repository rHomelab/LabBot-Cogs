# LabBot Privacy Policy

_Last updated: 2 November 2026_

## Who this covers

LabBot ("the bot", "we", "us") is a self-hosted moderation and community-utility Discord bot operated by the **r/Homelab Discord moderation team**. It runs on the open-source [Red-DiscordBot](https://github.com/Cog-Creators/Red-DiscordBot) ("Red") framework with custom ([LabBot-Cogs](https://github.com/rHomelab/LabBot-Cogs)) and third-party extensions ("cogs").

This policy explains what data the bot accesses through the Discord API, why, how long we keep it, how it is secured, and how you can access or delete it. It applies to the LabBot instance operated by the r/Homelab moderation team.

## Summary

- We collect only the data needed to run moderation and community features.
- We **do not** sell your data, share it with advertisers, or use it to train AI/ML models.
- Message content is used **transiently** for moderation (anti-phishing, channel rules, keyword auto-replies) and to process commands; we do not build profiles from your messages.
- Presence/activity is only ever stored as **anonymous aggregate counts**, never tied to an individual.
- Data is stored on our own infrastructure and is **encrypted at rest**.

## What data we access and why

### Data from your use of the bot

- **Commands you run.** When you invoke a command, the bot processes your message and may log the command name, channel, and timestamp for moderation accountability.
- **Opt-in account links & content.** If you use the Last.fm feature, we store the Last.fm username you choose to link to your Discord account. If you set reminders, we store the reminder text and time you provide. Tags/custom messages you create are stored with your user ID as creator/owner.

### Data used for moderation & community features

- **Moderation notes & warnings.** Moderators can record notes/warnings about a user. Each record contains the subject user's ID, the moderator-written text, the moderator's ID and name, and a timestamp. These are retained for ongoing moderation purposes.
- **Moderation case logs.** Moderation actions (e.g. timeouts, mutes, bans) are logged via Red's modlog and an extended mod-log cog, including the affected user's ID, the responsible moderator, a reason, and timestamps. When a message is deleted, its content may be logged to a moderator-only channel in Discord so moderators can review it for abuse, spam, or ban evasion.
- **Role & onboarding state.** To assign roles and send welcomes correctly, we store lists of member IDs who have completed onboarding, who have already been welcomed, and temporarily the roles a member held while in our "timeout" state, so they can be restored afterwards.
- **Purge exclusions.** User IDs that moderators have exempted from automated pruning of accounts that never verified.

### Message content

LabBot uses Discord's Message Content intent to: scan messages for known phishing/scam links and remove them; enforce per-channel content rules (length, required/forbidden media, account/guild age); respond to configured keyword triggers; and process prefix commands. Message content is processed in real time and is **not** retained to build profiles. When a message is deleted, our moderation tooling may log its content to a moderator-only channel in Discord so moderators can review it for abuse, spam, or ban evasion. It is not stored outside Discord and is not used to profile you. We do not otherwise retain message content. We do **not** use message content to train machine-learning or AI models.

### Presence & activity

LabBot uses the Presence intent only to produce **anonymous, aggregate counts** (for example, how many members are online/idle/offline, or how many are playing/streaming/listening). These counts contain no usernames, user IDs, or any per-user information, and no individual's presence or activity is stored or profiled. They are displayed as community activity graphs that members can view at https://labbot.tiga.tech.

## How your data is stored and secured

All persistent data is stored in the bot's own database on infrastructure we control. Data is **encrypted at rest.** Where off-site backups are used, they are also encrypted. Access is limited to the bot operators.

## Data retention

Moderation and operational data is retained for as long as it is needed for moderation and community management. In some cases this is indefinite, because historical moderation context remains relevant. You may request deletion at any time (see below). Anonymous aggregate statistics are not linked to you and are retained as long as they are useful.

## Third-party services & components

- **Self-hosted monitoring.** Anonymous aggregate statistics are stored in our own Prometheus instance and displayed via our own Grafana instance, accessible at https://labbot.tiga.tech. These are not third-party SaaS and the data is not shared externally.
- **Phishing blocklist.** The anti-phishing feature downloads a list of known scam domains from phish.sinking.yachts. Your messages are checked locally on our server and are **never** sent to that service.
- **Third-party cogs.** LabBot runs community-maintained cogs (e.g. Last.fm, reminders, moderation logging). Each handles only the data described above.

We do **not** sell, rent, or share your personal data with advertisers or unrelated third parties.

## Your rights: accessing and deleting your data

- **See what's stored:** run `^mydata whatdata` in the server (replace `^` with the bot's prefix) to see information about the data the bot's cogs hold about you.
- **Request deletion:** run `^mydata forgetme`, or contact the r/Homelab moderation team. The moderation team actions deletion requests; some records are removed manually, but genuine erasure requests are honored.
- Data needed to keep the community safe (e.g. active ban/evasion evidence) may be retained where we have a legitimate interest, consistent with Discord's Developer Policy and Terms.

## Children's privacy

LabBot is not directed at children. You must meet Discord's minimum age requirements to use Discord and this bot. We do not knowingly collect data from anyone under the applicable minimum age.

## Changes to this policy

We may update this policy as the bot's features change. Material changes will be announced in the server and reflected by the "last updated" date above.

## Contact

Questions or data requests: contact the r/Homelab moderation team via the Discord server (https://discord.gg/homelab).
