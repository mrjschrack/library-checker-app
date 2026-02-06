# Project Status

Last updated: 2026-02-06

## What Works
- Goodreads to-read sync via RSS and dashboard display.
- Multi-library availability checks with color badges.
- Libby/OverDrive deep link generation (when detected).
- Mobile-friendly dashboard layout.

## Known Issues
- Full-shelf refresh is slow and can trigger duplicate searches/badges.
- Availability matching can be inaccurate for some titles/editions.
- Refresh flow is all-or-nothing; no per-title refresh controls.

## Next Up
- Add per-title refresh and a global "Refresh All" with caching.
- Dedupe availability rows per book+library.
- Improve matching using ISBN/ASIN and fuzzy title+author fallback.
