# mars-vrchat-gallery
A gallery of cherished moments shared by Mars and his amazing friends in VRChat.
[vrchat.maao.cc](https://vrchat.maao.cc/)

---

You may feel free to create your own gallery based on this project, regardless the game.
*(whispers)* VRChat is such a nice game that you should definitely try!

---

## Local photo process commands

Just for notes.

```
process-photos
upload-photos
```

---

## Prototype

This prototype is a Vue, Vite, and TypeScript personal gallery. Metadata lives in JSON files:

- `src/data/photos.json`
- `src/data/friends.json`
- `src/data/worlds.json`
- `src/data/special-events.json`
- `src/data/tags.json`

The public photo binaries are stored in Cloudflare R2 rather than Git. Each photo has three variants. The PNG is post-processed first, then kept lossless; the JPG variants are compressed display copies:

- `original/<filename>.png`: the post-processed, lossless PNG exposed by the lightbox download action.
- `full/<filename>.jpg`: the full-size processed JPG used by the lightbox.
- `thumbnail/<filename>.jpg`: the resized JPG used in previews.

The only photo binary intentionally retained in the repository is the #293 demo copy at `public/photos/VRChat_2026-10-11_03-47-50.jpg`; all other `public/photos/` binaries are removed from the Git index during the R2 migration.

The gallery always loads photo assets from `https://r2.vrchat.marsinside.com`
in both development and production. The local #293 demo comparison JPG remains
under `public/photos/`; all normal gallery photos, thumbnails, and downloads use
the R2 bucket. The R2 bucket is
`mars-vrchat-gallery-photos`; the Cloudflare custom domain is
`r2.vrchat.marsinside.com`. The Aliyun-hosted `r2.vrchat.maao.cc` hostname can
be enabled after its DNS/Cloudflare custom-domain setup is complete.

Descriptions can reference friends by id with `[[friend_id]]`, for example
`[[eric]]`. The site renders the current display name from `friends.json`.

Linked moments use the `linked` field with numeric image ids. Child photos use
`parent` so they stay attached to the parent gallery card instead of appearing
as standalone outings.

The `captured` field is treated as GMT+8 when it does not include an explicit
timezone suffix. This keeps gallery dates stable for visitors in other
timezones while matching the VRChat screenshot filename time.

URLs can deep-link into the gallery flow. Use `#60` or `/60` to highlight photo
id 60. Special event ids work in the same way, such as
`#mars-17th-birthday` or `/mars-17th-birthday`. Hash filters such as
`#friend=taru` and `#world=after.glow` remain supported.

## Photo Tags

Lightbox photos can show Instagram-like friend tags. Tags live in
`src/data/tags.json` instead of `photos.json`:

```json
{
  "photo": 4,
  "tags": [
    {
      "friend": "mooncake",
      "x": 55.5,
      "y": 58.8
    },
    {
      "friend": "eric",
      "x": 77.9,
      "y": 71.9,
      "position": "right"
    }
  ]
}
```

Tag fields:

- `photo`: numeric image id from `photos.json`.
- `friend`: friend id from `friends.json`.
- `x` and `y`: percentage coordinates on the displayed image, from 0 to 100.
- `position`: optional label position, one of `top`, `right`, `bottom`, or
  `left`. When omitted, the label appears below the dot.

Tags follow the lightbox chrome visibility. Clicking the photo or zooming hides
the tags with the caption and controls.

While running the local dev server, the browser console exposes tag editing
helpers:

```js
tagsEdit.on()
tagsEdit.off()
tagsEdit.print()
await tagsEdit.save()
```

Use `tagsEdit.on()` with a photo open in the lightbox, drag the tag dots to
their real positions, then use `tagsEdit.print()` to print the current photo's
tag JSON. You can move through multiple photos and adjust tags in one session;
`await tagsEdit.save()` writes all current in-browser tag groups back to
`src/data/tags.json` through the local Vite dev server.

`tagsEdit.save()` only works during local development with `npm run dev`.
Production builds cannot write source files. For a quick coordinate template,
click anywhere on the lightbox image; the app will show and copy a starter JSON
block with that click's `x` and `y`.

## Special Events

Special events are configured in `src/data/special-events.json` and are
inserted into the normal gallery flow by photo time. They render as a full-width
module matching the current gallery stream width, so the event can sit between
regular outings without becoming a separate page.

Mark every photo that belongs to a special event in `photos.json`:

```json
{
  "id": 60,
  "filename": "VRChat_2026-06-15_23-36-26.jpg",
  "captured": "2026-06-15T23:36:26",
  "world": "birthday.celebration",
  "friend": ["persimmon"],
  "special-events": true
}
```

Those photos are removed from the ordinary gallery stream and shown by the
matching special event instead. They can still use `linked` and `parent` to keep
related photos grouped.

Example event:

```json
{
  "id": "mars-17th-birthday",
  "title_en": "Mars' 17th birthday party",
  "title_zh": "毛毛的 17 岁生日会",
  "date_en": "June 16, 2026",
  "date_zh": "2026 年 6 月 16 日",
  "show_full_date": true,
  "world": "birthday.celebration",
  "friends": ["persimmon", "tofu"],
  "description_en": "A small room, a cake, and friends showing up from VRChat.",
  "description_zh": "一个小房间、一块蛋糕，还有从 VRChat 赶来的朋友。",
  "photo_ids": [60, 61, 62, 63],
  "featured_photo_ids": [60, 62]
}
```

Special event fields:

- `photo_ids`: all photos shown inside the event.
- `featured_photo_ids`: large header photos. On desktop and tablet gallery
  layouts they appear in two columns; on mobile they stack into one column.
- `world`: event-level world. If a photo has the same world, the photo world is
  hidden to avoid repeating information. If it differs, the photo keeps its own
  world label.
- `friends`: event-level friends. They render below the description with the
  same `WITH` copy and friend-name handling as the gallery.
- `show_full_date`: when true, every event photo shows date and time, such as
  `June 16 at 12:01 AM`. When omitted or false, photos on the same gallery day
  collapse to time only, and cross-day photos show date and time without the
  year.

The event label is styled in green and event dates/times are styled in yellow.
Linked photos inside an event use compact gallery-like thumbnails.

## One-tap photo processing

The recommended one-command workflow starts with original PNG screenshots in
`~/Downloads`:

```bash
process-photos
```

This alias runs `scripts/process_photos.py`, which performs the steps in order:

1. Renames VRChat screenshots by removing milliseconds and resolution suffixes.
2. Keeps the renamed PNG originals in the input folder.
3. Converts each original PNG to a full-size JPG at quality 90 in `~/Downloads/full/`.
4. Converts the original PNG again to a JPG thumbnail at quality 60, with the
   longest edge limited to 640 pixels, in `~/Downloads/thumbnail/`.

Use another source folder when needed:

```bash
process-photos --input /path/to/original-pngs
```

Preview the operations without writing files:

```bash
python3 scripts/process_photos.py --dry-run
```

The old separate aliases have been replaced by `process-photos` in the local
shell configuration.

## R2 photo upload

Uploading is a separate step from local processing. After running
`process-photos`, upload all three variants with:

```bash
upload-photos
```

The upload alias runs `scripts/upload_photos.py` with `~/Downloads` as its
default input. It uploads:

```text
~/Downloads/*.png       → original/
~/Downloads/full/*.jpg  → full/
~/Downloads/thumbnail/*.jpg → thumbnail/
```

The script uses the local Wrangler CLI, uploads concurrently, sets image content
types, and targets the remote bucket `mars-vrchat-gallery-photos`. Preview the
manifest without uploading:

```bash
python3 scripts/upload_photos.py --dry-run
```

Upload only selected variants when needed:

```bash
python3 scripts/upload_photos.py --only full --only thumbnail
python3 scripts/upload_photos.py --only original
```

Use a different source directory with `--input /path/to/folder`.

## Scripts

`generate_photos_json.py` creates metadata templates from `~/Downloads` by
default. It normalizes new entries to the JPG display filename and keeps existing metadata
(including photo ids and annotations) unchanged:

```bash
python3 scripts/generate_photos_json.py --input /path/to/staging --output src/data
python3 scripts/tags.py
python3 scripts/batch_rename.py --input /path/to/staging
python3 scripts/batch_png_to_jpg.py --input /path/to/staging
python3 scripts/batch_resize.py --input /path/to/staging
```

The normal production workflow is to upload the three generated variants to R2
under `original/`, `full/`, and `thumbnail/`, then commit only metadata changes
to Git. Do not add `public/photos/` to Git; it is ignored after the R2 migration.

When no `--input` is provided, it reads `~/Downloads`. Use `--input` for another folder.

Preview metadata generation without writing:

```bash
python3 scripts/generate_photos_json.py --dry-run
python3 scripts/tags.py --dry-run
```

## R2 setup

The bucket and mirror custom domain are already configured in Cloudflare:

```text
Bucket: mars-vrchat-gallery-photos
Custom domain: r2.vrchat.marsinside.com
Location hint: APAC
```

The repository includes `r2-cors.json` for browser downloads from both gallery
domains and local Vite development. Apply it with:

```bash
npx wrangler r2 bucket cors set mars-vrchat-gallery-photos --file r2-cors.json
```

No asset environment variable is needed; the frontend uses the R2 custom
domain directly. Until the R2 objects are uploaded, normal gallery image URLs
will be unavailable.

## Development

```bash
npm install
npm run dev
```

For a production build:

```bash
npm run build
```

## Steam VRChat playtime

The statistics page can display Steam playtime for VRChat (Steam AppID
`438100`) through the separate Cloudflare Worker in `worker/index.ts`. The
Steam API key and SteamID64 are Worker secrets and are never sent to the
browser.

Set the secrets before deploying:

```bash
npx wrangler secret put STEAM_API_KEY --config wrangler.jsonc
npx wrangler secret put STEAM_ID --config wrangler.jsonc
npm run worker:deploy
```

The Worker serves `GET https://vrchat-statistics.marsinside.com/api/steam-playtime`.
Its custom domain and `ALLOWED_ORIGINS` list are configured in `wrangler.jsonc`.
Both `https://vrchat.maao.cc` and `https://vrchat.marsinside.com` are allowed.
The frontend endpoint is configured in `src/statistics.json` as `steamApiEndpoint`;
`VITE_STEAM_API_URL` is a fallback when that config value is empty.
If the Steam profile or game details are private, Steam will not
return the playtime. Mobile playtime is maintained manually in
`src/statistics.json` and displayed alongside the Steam value. Set
`"show-mobile-hours": false` there to hide the breakdown and show only the
VRCHAT PLAYTIME total.

To publish the site after changing gallery data or `src/statistics.json`:

```bash
npm install
npm run build
npx wrangler pages deploy dist --project-name mars-vrchat-gallery
```

The Pages project is `mars-vrchat-gallery` and its production domain is
`https://vrchat.maao.cc/`.

For the Aliyun-hosted primary, configure its static host to serve
`index.html` for direct requests to `/123` and event paths such as
`/mars-17th-birthday` (the included `deploy/aliyun.nginx.conf` shows the Nginx
rewrite form). Cloudflare Pages already handles the SPA fallback through
`public/_redirects`.
