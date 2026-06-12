# Maintainer stats

How to see whether anyone is using Markwell. Maintainer-only; nothing here is
needed by readers.

## Release downloads (desktop zips)

Per-asset, all releases:

```bash
gh api repos/ceparadise168/markwell/releases --jq '.[].assets[] | [.name, .download_count] | @tsv'
```

The README's downloads badge (`img.shields.io/github/downloads/ceparadise168/markwell/total`)
shows the all-time total automatically — no setup, no token.

## PyPI installs

```bash
pipx run pypistats recent markwell
```

Data lags about a day, and only exists once the package is published. For a
breakdown over time: `pipx run pypistats overall markwell`.

## Repo traffic

GitHub → repository → **Insights → Traffic**: clones and unique visitors,
rolling 14-day window (it is not stored beyond that — check in occasionally
or it's gone). Stars/watchers are on the repo front page.

## Site traffic

Cloudflare dashboard → **Web Analytics** → the Markwell site. Privacy-friendly
(no cookies); shows visits and referrers once the landing site is deployed
with analytics toggled on.
