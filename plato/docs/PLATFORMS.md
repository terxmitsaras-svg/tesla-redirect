# PLATO on every platform

PLATO has one server and three ways to use it:

| Piece | What it is | Runs on |
|---|---|---|
| **PLATO server** | API + web app (runs your agents) | Windows, macOS, Linux, Kali, Chromebook (Linux), or Docker |
| **PLATO app** | the web app installed as an app (PWA): own window/icon, full screen on phones | Windows, macOS, Linux, ChromeOS, Android, iPhone/iPad |
| **`plato` CLI** | terminal client: run, watch and steer agents | PowerShell / cmd / Windows Terminal, macOS Terminal, Linux / Kali / ChromeOS shells |

Phones and tablets don't run the server: they connect to a PLATO server on your computer (same Wi-Fi)
or on the internet.

## At a glance

| Platform | Server | App | CLI |
|---|---|---|---|
| Windows 10/11 | `scripts\install.ps1`, `scripts\start.ps1` | Edge/Chrome → **Install** | `plato` in PowerShell / cmd |
| macOS | `scripts/install.sh`, `scripts/start.sh` | Chrome/Edge → **Install**; Safari → **File → Add to Dock** | `plato` in Terminal |
| Linux (Ubuntu, Debian, Fedora, Arch…) | `scripts/install.sh` | Chrome/Edge/Chromium → **Install** | `plato` |
| Kali Linux | `scripts/install.sh` | Chromium → **Install** (or use Firefox as a normal site) | `plato` |
| Chromebook | in **Linux development environment**: `scripts/install.sh` | Chrome → **Install** | `plato` in the Linux terminal |
| Android | connect to a server | Chrome → **Install app** | (Termux: `pip install ./cli`, untested) |
| iPhone / iPad | connect to a server | Safari → Share → **Add to Home Screen** | n/a |

## Windows (PowerShell)

1. Install prerequisites (once), then open a **new** PowerShell window:
   ```powershell
   winget install -e --id Python.Python.3.12
   winget install -e --id OpenJS.NodeJS.LTS
   ```
2. In the `plato` folder:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
   .\scripts\start.ps1            # or: .\scripts\start.ps1 -Lan   (phones on your Wi-Fi)
   ```
   `-ExecutionPolicy Bypass` affects only that one command; it doesn't change your system policy.
   With `-Lan`, Windows Firewall asks once: allow **Private networks** only.
3. Open http://localhost:3000 in Edge or Chrome, then **⋯ → Apps → Install PLATO** (or the install icon in
   the address bar). PLATO gets a Start-menu entry and its own window.
4. Terminal: `.\.venv\Scripts\plato.exe --help` (or `pipx install .\cli` to put `plato` on your PATH).

Works in Windows PowerShell 5.1 (built into Windows) and PowerShell 7. The scripts are plain ASCII and
call `npm.cmd` directly, so the default execution policy and code page don't interfere.

## macOS

```bash
brew install python@3.12 node        # once
./scripts/install.sh
./scripts/start.sh                   # or --lan
```
Install the app from Chrome/Edge (**Install** icon in the address bar) or Safari 17+ (**File → Add to Dock**).

## Linux, Kali Linux

```bash
sudo apt install -y python3 python3-venv python3-pip   # Debian/Ubuntu/Kali; see the installer's hints for others
# Node.js 20.9+ (distro packages are often older): https://nodejs.org or `fnm install 22`
./scripts/install.sh
./scripts/start.sh
```
Kali: everything runs as your normal user; no root needed after installing packages. Python 3.11+ is
required (Kali rolling ships newer).

## Chromebook

1. Turn on Linux: open **Settings**, search for **Linux**, choose **Linux development environment →
   Turn on**. (ChromeOS's Linux is Debian-based; PLATO needs Python 3.11+, which Debian 12 and later provide.)
2. In the Linux terminal: install Python/Node as for Debian above, then `./scripts/install.sh` and
   `./scripts/start.sh`.
3. Open http://localhost:3000 in Chrome and click **Install**; PLATO appears in the launcher like any
   app. If localhost doesn't load, try http://penguin.linux.test:3000 (also accepted by PLATO).

## Android and iPhone/iPad

1. On your computer: `./scripts/start.sh --lan` (Windows: `.\scripts\start.ps1 -Lan`). It prints an
   address like `http://192.168.1.20:3000`.
2. Open that address on the phone (same Wi-Fi).
   - **Android (Chrome):** ⋮ → **Install app** / **Add to Home screen**.
   - **iPhone/iPad (Safari):** Share → **Add to Home Screen**. PLATO's **Install app** button shows these steps.

**HTTPS matters on phones.** Over plain `http://` on a LAN, phones can add PLATO to the home screen,
but browsers only enable offline support and the full install prompt on `https://` (or `localhost`).
For a proper app experience and for use away from home, serve PLATO over HTTPS with the included
Caddy config ([`deploy/Caddyfile`](../deploy/Caddyfile)): one address, `/api` and `/ws` go to the API,
everything else to the web app.

```bash
cd frontend && NEXT_PUBLIC_API_URL=same-origin npm run build && cd ..
./scripts/start.sh
PLATO_SITE=plato.example.com caddy run --config deploy/Caddyfile   # real domain → automatic trusted certificate
```

To reach your home server from your phone anywhere without opening ports, join both to a
[Tailscale](https://tailscale.com) network: `http://100.x.y.z:3000` works out of the box (PLATO accepts
Tailscale addresses), and Tailscale can issue an HTTPS certificate for the machine's `*.ts.net` name
to use as `PLATO_SITE`.

Without a reverse proxy, the web app finds the API automatically at the same host on port 8000, so
the same build works on `localhost`, a LAN IP, or a Tailscale IP.

## The `plato` CLI

See [cli/README.md](../cli/README.md). Quick taste:

```powershell
plato login --server http://localhost:8000
plato run "Launch plan" "Design the data model and API" # streams live; Ctrl+C stops the run
plato say "Launch plan" "Focus on the API" --to Developer # from another terminal
```

## Security notes for LAN mode

- `--lan` / `-Lan` exposes the sign-in page to your local network. Use it on networks you trust.
- In development, the API accepts browser requests from private-network origins (192.168.x.x, 10.x,
  172.16–31.x, `*.local`, Tailscale 100.64/10). In production (`PLATO_ENV=production`) it accepts
  only `PLATO_CORS_ORIGINS` (and `PLATO_CORS_ORIGIN_REGEX` if you set one).
- The installers create `.env` with fresh secrets, readable only by you (`chmod 600` / Windows ACL).

## What is verified, and how

| Platform | Verification |
|---|---|
| Linux | installer, start script, API + CLI test suites (Python 3.11 and 3.13), browser end-to-end runs |
| Linux · PowerShell 7 | `install.ps1` + `start.ps1` run end to end; CLI driven from PowerShell incl. `ConvertFrom-Json`; PSScriptAnalyzer clean (except Write-Host style rule) |
| Android (Pixel 7 emulation, Chromium) | full agent run over a LAN hostname, no layout overflow |
| iPhone 15 (layout emulation in Chromium) | full agent run, no layout overflow. **Safari/WebKit itself was not available to test** |
| PWA (Chromium) | installable with zero installability errors; service worker active; offline page works |
| HTTPS via Caddy (`same-origin`) | full browser demo through Caddy 2.6 over HTTPS: REST, secure WebSockets, streaming, stop, refresh |
| Windows (PowerShell 5.1), macOS | **not yet verified.** CI jobs exist for both (test suites, installers, start scripts, an agent run via the CLI), but GitHub has not started any job on this repository (no runner assigned; the repository's other workflow fails the same way), which points to an account-level Actions setting. Once Actions runs, the `PLATO CI` workflow verifies these |
| Kali, Chromebook | same code path as Debian/Linux; not run on those devices |

Native app-store apps (Microsoft Store, Mac App Store, Google Play, App Store) are not built: the
installable web app covers these platforms from one codebase. Store packaging can wrap the same app
later (e.g. Tauri for desktop, Capacitor for mobile) and needs signing accounts on each platform.
