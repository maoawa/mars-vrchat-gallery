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

Full-size photos are loaded from `public/photos/`. Thumbnails are loaded from
`public/photos/thumbnails/` with the same filename.

Descriptions can reference friends by id with `[[friend_id]]`, for example
`[[eric]]`. The site renders the current display name from `friends.json`.

Linked moments use the `linked` field with numeric image ids.

To add blank templates for new `VRChat_*.png` files in `public/photos/`:

```bash
python3 scripts/generate_images_json.py
```

The script reads the current `src/data/images.json`, skips filenames already in
the file, and appends new templates with the next available numeric ids.

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
