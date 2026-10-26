# Security & privacy

SnapType installs a global keyboard hook, so you should know exactly what it does.

- **Local only.** No network code, no telemetry, no accounts.
- **Typed text is never stored or logged.** Only the last few letters of the
  current word are held in memory, cleared on any non-letter key, modifier
  combo, or 4 seconds of idle time. The log records events and errors, not text.
- **Window titles** are read locally, only to apply App Rules and to skip
  password / sign-in windows.
- **Data** lives in `%APPDATA%\SnapType` (`snippets.json`, `config.json`,
  `stats.json`, `snaptype.log`).
- Antivirus tools sometimes flag any keyboard-hooking app. Verify releases with
  the published SHA-256 and build from source if in doubt.

Report vulnerabilities privately via the email on the GitHub profile rather than a public issue.
