# Qadreen

An advanced NVDA add-on designed for the Qadreen community, providing robust cloud-based synchronization and centralized management for software links and resources. The add-on streamlines workflows for both supervisors and end users through automated background synchronization and native NVDA interface dialogs.

## Features

- **Transactional Cloud Synchronization Engine:** Robust, non-blocking background sync powered by a 3-way merge engine and pending-state tracking. Local changes by repository owners are strictly protected against restart overwrite or data loss.
- **On-Demand Manual Sync:** Dedicated "Sync Now" button inside the main search dialog for repository owners in Central Online Design Mode, providing instantaneous atomic pushes to GitHub.
- **Automated Conflict Resolution:** Native handling of HTTP 409/422 conflicts via automatic remote re-fetch and delta recalculation without interrupting user workflow.
- **Collaborator Contribution Support:** Safe multi-user workflow allowing designated collaborators to contribute new software entries without risking repository structure or owner-managed records.
- **Secure Credential Storage:** Sensitive GitHub Personal Access Tokens (PAT) are encrypted at rest using the Windows Data Protection API (DPAPI).
- **Cloud Design Mode:** Dedicated supervisor mode enabling authorized repository owners to add, configure, move, and publish software resources directly via standard dialogs.
- **Accessible UI Architecture:** Interface elements built with `gui.guiHelper` adhering strictly to NVDA core standards, supporting high-DPI scaling and responsive screen-reader focus routing.
- **Independent Localization:** Built-in multi-language engine supporting dynamic language switching (Arabic, English, or NVDA system match).

## Keyboard Shortcuts

| Shortcut | Description |
| :--- | :--- |
| `NVDA+Control+H` | Open the non-modal Help Guide dialog to browse documentation and resources. |
| `NVDA+Shift+C` | Open the interactive dialog to create and program a new resource link (Supervisor Mode). |
| `NVDA+Control+Shift+D` | Authenticate repository ownership and toggle Cloud Design Mode. |

## Compatibility

- **Minimum NVDA Version:** `2025.1`
- **Last Tested NVDA Version:** `2026.2`
- **Operating System:** Windows 10 / Windows 11 (64-bit)

## Configuration

The settings panel is integrated directly into NVDA:
`NVDA Menu -> Preferences -> Settings -> Qadreen`

Available options:
1. **GitHub Repository:** Target repository path (`owner/repository`).
2. **Access Token:** Secure storage for your GitHub Personal Access Token (PAT).
3. **Language Preference:** Force interface language to Arabic, English, or follow NVDA default.

## Author

- **Saeed Mohamed Atia**
- Email: `saedmohamed.n2210@gmail.com`
- Repository: [https://github.com/saedmohamedn2210-create/Qadreen](https://github.com/saedmohamedn2210-create/Qadreen)