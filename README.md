# mars-vrchat-gallery
A gallery of cherished moments shared by Mars and his amazing friends in VRChat.
[vrc.maao.cc](vrchat.maao.cc)

---

You may feel free to create your own gallery based on this project, regardless the game.
*(whispers)* VRChat is such a nice game that you should definitely try!

## Prototype

This prototype is a Vue, Vite, and TypeScript personal gallery. Metadata lives in JSON files:

- `src/data/images.json`
- `src/data/friends.json`
- `src/data/worlds.json`
- `src/data/special-events.json`

Full-size photos are loaded from `public/photos/`. Thumbnails are loaded from
`public/photos/thumbnails/` with the same filename.

Descriptions can reference friends by id with `[[friend_id]]`, for example
`[[eric]]`. The site renders the current display name from `friends.json`.

Linked moments use the `linked` field with numeric image ids. Child photos use
`parent` so they stay attached to the parent gallery card instead of appearing
as standalone outings.

The `captured` field is treated as UTC+8 when it does not include an explicit
timezone suffix. This keeps gallery dates stable for visitors in other
timezones while matching the VRChat screenshot filename time.

URLs can deep-link into the gallery flow. Use `#60` to scroll to photo id 60,
or use a special event id such as `#mars-17th-birthday` to scroll to that event.

## Special Events

Special events are configured in `src/data/special-events.json` and are
inserted into the normal gallery flow by photo time. They render as a full-width
module matching the current gallery stream width, so the event can sit between
regular outings without becoming a separate page.

Mark every photo that belongs to a special event in `images.json`:

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

## Scripts

To add blank templates for new `VRChat_*.png`, `VRChat_*.jpg`, or
`VRChat_*.jpeg` files in `public/photos/`:

```bash
python3 scripts/generate_images_json.py
```

With custom folders:

```bash
python3 scripts/generate_images_json.py --input public/photos --output src/data
python3 scripts/batch_rename.py --input raw-photos
python3 scripts/batch_resize.py --input public/photos
python3 scripts/batch_png_to_jpg.py --input public/photos
```

`batch_rename.py` renames `.png`, `.jpg`, and `.jpeg` files in place while
preserving their file extension. `batch_resize.py` writes thumbnails to
`INPUT/thumbnails/` unless `--output` is provided, and keeps JPEG output as
JPEG and PNG output as PNG. `batch_png_to_jpg.py` converts `VRChat_*.png`
files to same-name `.jpg` files in `INPUT/` unless `--output` is provided, and
skips existing JPG files unless `--overwrite` is passed.

`generate_images_json.py` writes to `src/data/images.json` by default. The
script reads the current JSON file, skips filenames already in the file, and
appends new templates with the next available numeric ids. It accepts
`VRChat_YYYY-MM-DD_HH-MM-SS.png`, `.jpg`, and `.jpeg` filenames.

Preview without writing:

```bash
python3 scripts/generate_images_json.py --dry-run
```

## Development

```bash
npm install
npm run dev
```

For a production build:

```bash
npm run build
```
