# Back up Markwell to your cloud

**English** · [中文（台灣）](cloud-backup.zh-TW.md) · [日本語](cloud-backup.ja.md) · [한국어](cloud-backup.ko.md)

A guide to keeping your Markwell library in iCloud Drive, Google Drive,
Dropbox, or OneDrive — and getting it back, intact, on a new computer. No new
account, no setup beyond a few clicks.

## Why this works

Everything Markwell saves lives in one ordinary folder of ordinary files: your
saved copies in `backups/`, your readable pages and exports in `output/`, and
any ZIP archives you create. Cloud services are already good at syncing a
folder — so Markwell doesn't need your password, doesn't talk to any cloud
API, and never asks you to create an account. You simply keep the Markwell
folder *inside* the folder your cloud app already syncs, and the cloud app
does the rest.

Markwell itself never uploads anything. It makes no network connections at
all — the syncing is done entirely by the cloud app you already trust with
your other files (see [SECURITY.md](../SECURITY.md)).

## Move your library into your cloud

You need the cloud's own desktop app installed and signed in first — the app
from Apple, Google, Dropbox, or Microsoft that keeps a folder on your computer
in sync. Then, in Markwell:

1. Open **Settings** in the sidebar.
2. Under **Where your Markwell folder lives**, the clouds found on your
   computer are offered as choices — pick yours.
3. Press **Keep my library here**.
4. Markwell tells you exactly what is about to happen — everything is *copied*
   to the new folder, and your old files stay where they are. Press
   **Copy my library there**.

That's it. The report shows how many saved copies and files were copied, and
where your old files still live — **nothing is ever deleted**. From now on,
every backup you make lands in the cloud folder, and your cloud app uploads it
automatically.

Markwell keeps your library in a folder named `Markwell` at the top of your
cloud folder, so it is easy to find from any of your devices.

## Provider notes

The steps inside Markwell are the same for every provider; the only difference
is which desktop app needs to be installed:

- **iCloud Drive** — built into macOS: if you use iCloud, it is already there.
  On Windows, install **iCloud for Windows** from the Microsoft Store and turn
  on iCloud Drive.
- **Google Drive** — install **Google Drive for desktop** and sign in; a
  synced Google Drive location appears on your computer.
- **Dropbox** — install the **Dropbox** desktop app and sign in.
- **OneDrive** — built into Windows: if you use OneDrive, it is already
  syncing. On macOS, install **OneDrive** from the App Store and sign in.

If your cloud still doesn't appear in Settings, see the FAQ below.

## Moving to a new computer

Your library follows you. On the new computer:

1. Install your cloud's desktop app, sign in, and give it a moment to finish
   syncing.
2. Install Markwell — see [Get Markwell](../README.md#get-markwell).
3. Open **Settings**, pick the same cloud, and confirm.

Markwell points itself at the same `Markwell` folder in your cloud — and your
books, highlights, notes, and every saved copy are already in it. Open
**Library** to read, or **History** to see your saved copies.

## FAQ

**My cloud doesn't show up in Settings.**
Markwell offers a cloud only when it can find that cloud's synced folder on
this computer. Make sure the provider's desktop app is installed and signed
in. If your cloud folder lives somewhere unusual, choose **Advanced: a folder
I choose** and type the full path of a folder inside it — for example
`/Users/you/Dropbox/Markwell`.

**What exactly gets synced?**
Whatever is in your Markwell folder: `backups/` (your saved copies), `output/`
(your readable pages and exports), and any `Markwell-archive-….zip` you've
created. Markwell's small settings file lives outside the library (in
`~/.markwell/`), so each computer keeps its own — by design.

**Does Markwell upload my highlights anywhere?**
Never. Markwell makes no network connections; all syncing is done by your
cloud provider's own app, under that app's account and rules. Turn the cloud
app off and the folder simply stays local.

---

← [Back to the README](../README.md)
