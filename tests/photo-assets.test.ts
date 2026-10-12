import assert from 'node:assert/strict'
import { test } from 'node:test'
import { galleryRouteTarget, photoAssetFilename, photoAssetUrl } from '../src/utils/photo-assets.ts'

test('three asset variants map legacy metadata names to real formats', () => {
  for (const ext of ['png', 'jpg', 'jpeg', 'PNG', 'JPEG']) {
    const filename = `VRChat_2026-10-13_00-00-00.${ext}`
    assert.equal(photoAssetUrl('https://r2.example.com/', 'full', filename), 'https://r2.example.com/full/VRChat_2026-10-13_00-00-00.jpg')
    assert.equal(photoAssetUrl('https://r2.example.com', 'thumbnail', filename), 'https://r2.example.com/thumbnail/VRChat_2026-10-13_00-00-00.jpg')
    assert.equal(photoAssetUrl('https://r2.example.com', 'original', filename), 'https://r2.example.com/original/VRChat_2026-10-13_00-00-00.png')
  }
  assert.equal(photoAssetFilename('photo.JPG', 'png'), 'photo.png')
  assert.equal(photoAssetUrl('/assets/v2///', 'full', 'a #1.png'), '/assets/v2/full/a%20%231.jpg')
})

test('path links and hash links resolve identically, with hash priority', () => {
  assert.equal(galleryRouteTarget('/123', ''), '123')
  assert.equal(galleryRouteTarget('/123/', ''), '123')
  assert.equal(galleryRouteTarget('/', '#123'), '123')
  assert.equal(galleryRouteTarget('/123', '#124'), '124')
  assert.equal(galleryRouteTarget('/123', '#friend=taru'), 'friend=taru')
  assert.equal(galleryRouteTarget('/', '#world=after.glow'), 'world=after.glow')
  assert.equal(galleryRouteTarget('/', '#mars-17th-birthday'), 'mars-17th-birthday')
  assert.equal(galleryRouteTarget('/', ''), '')
  assert.equal(galleryRouteTarget('/statistics', ''), '')
  assert.equal(galleryRouteTarget('/mars-17th-birthday', ''), 'mars-17th-birthday')
  assert.equal(galleryRouteTarget('/unknown', ''), 'unknown')
  assert.equal(galleryRouteTarget('/', '#%E0%A4%A'), '')
})
