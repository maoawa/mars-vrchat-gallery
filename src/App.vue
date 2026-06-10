<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import LazyPhoto from './components/LazyPhoto.vue'
import friendsData from './data/friends.json'
import imagesData from './data/images.json'
import worldsData from './data/worlds.json'
import type { Friend, GalleryImage, GalleryRow, World } from './types'
import { daysSinceVrchatStart, formatGalleryDate, photoPath, thumbnailPath } from './utils/gallery'

type GalleryFilter =
  | {
      type: 'world'
      id: string
    }
  | {
      type: 'friend'
      id: string
    }

const friends = friendsData as Friend[]
const worlds = worldsData as World[]
const photos = [...(imagesData as GalleryImage[])].sort((a, b) => b.captured.localeCompare(a.captured))

const friendsById = new Map(friends.map((friend) => [friend.id, friend]))
const worldsById = new Map(worlds.map((world) => [world.id, world]))
const photosById = new Map(photos.map((photo) => [photo.id, photo]))

const allGalleryRows: GalleryRow[] = photos
  .filter((photo) => !photo.parent)
  .map((photo) => ({
    photo,
    linkedPhotos: (photo.linked ?? [])
      .map((linkedPhotoId) => photosById.get(linkedPhotoId))
      .filter((linkedPhoto): linkedPhoto is GalleryImage => Boolean(linkedPhoto)),
  }))

const now = ref(Date.now())
const activeIndex = ref<number | null>(null)
const zoomLevel = ref(1)
const activeFilter = ref<GalleryFilter | null>(null)
const galleryColumnCount = ref(1)
const lightboxStage = ref<HTMLElement | null>(null)

let clockTimer: number | undefined

const galleryRows = computed(() => {
  if (!activeFilter.value) {
    return allGalleryRows
  }

  return allGalleryRows.filter((row) => {
    const rowPhotos = [row.photo, ...row.linkedPhotos]
    return rowPhotos.some((photo) => photoMatchesFilter(photo, activeFilter.value))
  })
})

const lightboxPhotos = computed(() => galleryRows.value.flatMap((row) => [row.photo, ...row.linkedPhotos]))
const galleryColumns = computed(() => {
  const columns: Array<Array<{ row: GalleryRow; index: number }>> = Array.from(
    { length: galleryColumnCount.value },
    () => [],
  )

  galleryRows.value.forEach((row, index) => {
    columns[index % galleryColumnCount.value].push({ row, index })
  })

  return columns
})

const activePhoto = computed(() => {
  if (activeIndex.value === null) {
    return null
  }

  return lightboxPhotos.value[activeIndex.value] ?? null
})

const activePosition = computed(() => (activeIndex.value === null ? 0 : activeIndex.value + 1))
const daysInVrchat = computed(() => daysSinceVrchatStart(now.value))
const imageCount = computed(() => photos.length)
const outingCount = computed(() => allGalleryRows.length)
const filteredOutingCount = computed(() => galleryRows.value.length)
const zoomLabel = computed(() => `${Math.round(zoomLevel.value * 100)}%`)

const activeFilterLabel = computed(() => {
  if (!activeFilter.value) {
    return ''
  }

  if (activeFilter.value.type === 'world') {
    return worldName(activeFilter.value.id)
  }

  return friendName(activeFilter.value.id)
})

const zoomSurfaceStyle = computed(() => ({
  width: `${zoomLevel.value * 100}%`,
  height: `${zoomLevel.value * 100}%`,
}))

function worldFor(photo: GalleryImage) {
  return worldsById.get(photo.world) ?? { id: photo.world, name: photo.world }
}

function hasWorld(photo: GalleryImage) {
  return photo.world.trim().length > 0
}

function worldName(worldId: string) {
  return worldsById.get(worldId)?.name ?? worldId
}

function friendName(friendId: string) {
  return friendsById.get(friendId)?.name ?? friendId
}

function friendList(photo: GalleryImage) {
  return photo.friend
    .filter((friendId) => friendId.trim().length > 0)
    .map((friendId) => ({
      id: friendId,
      name: friendName(friendId),
    }))
}

function hasDescription(photo: GalleryImage) {
  return photo.description.trim().length > 0
}

function descriptionParts(description: string) {
  const parts: Array<{ type: 'text'; text: string } | { type: 'friend'; id: string; name: string }> = []
  const friendReferencePattern = /\[\[([a-zA-Z0-9_-]+)\]\]/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = friendReferencePattern.exec(description))) {
    if (match.index > lastIndex) {
      parts.push({ type: 'text', text: description.slice(lastIndex, match.index) })
    }

    parts.push({
      type: 'friend',
      id: match[1],
      name: friendName(match[1]),
    })
    lastIndex = match.index + match[0].length
  }

  if (lastIndex < description.length) {
    parts.push({ type: 'text', text: description.slice(lastIndex) })
  }

  return parts
}

function photoMatchesFilter(photo: GalleryImage, filter: GalleryFilter | null) {
  if (!filter) {
    return true
  }

  if (filter.type === 'world') {
    return photo.world === filter.id
  }

  return photo.friend.includes(filter.id)
}

function applyWorldFilter(worldId: string, closeAfterApply = false) {
  activeFilter.value = { type: 'world', id: worldId }
  activeIndex.value = null

  if (closeAfterApply) {
    closeLightbox()
  }

  requestAnimationFrame(() => {
    document.querySelector('.gallery')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

function applyFriendFilter(friendId: string, closeAfterApply = false) {
  activeFilter.value = { type: 'friend', id: friendId }
  activeIndex.value = null

  if (closeAfterApply) {
    closeLightbox()
  }

  requestAnimationFrame(() => {
    document.querySelector('.gallery')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

function clearFilter() {
  activeFilter.value = null
  activeIndex.value = null
}

function formatLinkedDate(photo: GalleryImage, parentPhoto: GalleryImage) {
  return isSameGalleryDay(photo, parentPhoto) ? formatTime(photo.captured) : formatGalleryDate(photo.captured)
}

function isSameGalleryDay(photo: GalleryImage, parentPhoto: GalleryImage) {
  return photo.captured.slice(0, 10) === parentPhoto.captured.slice(0, 10)
}

function formatTime(capturedAt: string) {
  const [, timePart = '00:00:00'] = capturedAt.split('T')
  const [hours = 0, minutes = 0] = timePart.split(':').map(Number)
  const meridiem = hours >= 12 ? 'PM' : 'AM'
  const hour12 = hours % 12 || 12

  return `${hour12}:${String(minutes).padStart(2, '0')} ${meridiem}`
}

function openPhoto(photoId: number) {
  const index = lightboxPhotos.value.findIndex((photo) => photo.id === photoId)

  if (index >= 0) {
    activeIndex.value = index
    zoomLevel.value = 1
  }
}

function closeLightbox() {
  activeIndex.value = null
  zoomLevel.value = 1
}

function showPreviousPhoto() {
  if (activeIndex.value === null || !lightboxPhotos.value.length) {
    return
  }

  activeIndex.value = (activeIndex.value - 1 + lightboxPhotos.value.length) % lightboxPhotos.value.length
  zoomLevel.value = 1
}

function showNextPhoto() {
  if (activeIndex.value === null || !lightboxPhotos.value.length) {
    return
  }

  activeIndex.value = (activeIndex.value + 1) % lightboxPhotos.value.length
  zoomLevel.value = 1
}

function centreZoomStage() {
  const stage = lightboxStage.value

  if (!stage) {
    return
  }

  stage.scrollLeft = (stage.scrollWidth - stage.clientWidth) / 2
  stage.scrollTop = (stage.scrollHeight - stage.clientHeight) / 2
}

function updateGalleryColumnCount() {
  if (window.innerWidth >= 1040) {
    galleryColumnCount.value = 3
    return
  }

  if (window.innerWidth >= 700) {
    galleryColumnCount.value = 2
    return
  }

  galleryColumnCount.value = 1
}

function handleKeydown(event: KeyboardEvent) {
  if (!activePhoto.value) {
    return
  }

  if (event.key === 'Escape') {
    closeLightbox()
  }

  if (event.key === 'ArrowLeft') {
    showPreviousPhoto()
  }

  if (event.key === 'ArrowRight') {
    showNextPhoto()
  }
}

watch(activePhoto, (photo) => {
  document.body.classList.toggle('lightbox-open', Boolean(photo))

  if (photo) {
    nextTick(centreZoomStage)
  }
})

watch(zoomLevel, () => {
  if (activePhoto.value) {
    nextTick(centreZoomStage)
  }
})

onMounted(() => {
  updateGalleryColumnCount()
  clockTimer = window.setInterval(() => {
    now.value = Date.now()
  }, 60_000)

  window.addEventListener('resize', updateGalleryColumnCount)
  window.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  if (clockTimer) {
    window.clearInterval(clockTimer)
  }

  window.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('resize', updateGalleryColumnCount)
  document.body.classList.remove('lightbox-open')
})
</script>

<template>
  <main class="site-shell">
    <header class="site-header">
      <h1>Mars VRChat Gallery</h1>
      <p class="lede">
        Hi! I'm Mars. As you can see, this is my personal VRChat gallery. It's still under construction so I may
        forget to mention some friends. But I didn't mean to ignore them, and I do cherish every friends of mine.
        Please contact me using methods in <a href="https://maao.cc/" target="_blank" rel="noreferrer">maao.cc</a>
        or in game. Thanks for appearing in my life and I love you guys!
      </p>
      <p class="lede lede-cn">
        嗨！我是毛毛。正如你所见，这是我的个人 VRChat 画廊。这里仍在建设中，所以我可能会不小心漏掉一些朋友。但我绝不是有意忽略他们，我真心珍视我的每一位朋友。请通过
        <a href="https://maao.cc/" target="_blank" rel="noreferrer">maao.cc</a>
        上的方式或直接在游戏里联系我。感谢你们出现在我的生活中，我爱你们！
      </p>
      <p class="lede lede-note">
        This website will be available in Chinese soon.<br />
        本网站将很快支持中文。
      </p>
    </header>

    <section v-if="activeFilter" class="filter-strip" aria-live="polite">
      <p>
        Showing {{ filteredOutingCount }} {{ filteredOutingCount === 1 ? 'outing' : 'outings' }} for
        <span>{{ activeFilterLabel }}</span>
      </p>
      <button type="button" @click="clearFilter">Clear</button>
    </section>

    <section class="gallery" aria-label="VRChat photos">
      <div v-for="(column, columnIndex) in galleryColumns" :key="columnIndex" class="gallery-column">
      <article v-for="entry in column" :key="entry.row.photo.id" class="photo-card">
        <button
          class="photo-trigger"
          type="button"
          :aria-label="`Open ${entry.row.photo.filename}`"
          @click="openPhoto(entry.row.photo.id)"
        >
          <LazyPhoto
            :src="thumbnailPath(entry.row.photo.filename)"
            :alt="entry.row.photo.description || entry.row.photo.filename"
            :eager="entry.index === 0"
          />
        </button>

        <div class="photo-body">
          <div class="photo-kicker">
            <span class="photo-number">#{{ entry.row.photo.id }}</span>
            <time :datetime="entry.row.photo.captured">{{ formatGalleryDate(entry.row.photo.captured) }}</time>
            <button v-if="hasWorld(entry.row.photo)" type="button" @click="applyWorldFilter(entry.row.photo.world)">
              {{ worldFor(entry.row.photo).name }}
            </button>
          </div>

          <p v-if="hasDescription(entry.row.photo)" class="photo-description">
            <template v-for="(part, index) in descriptionParts(entry.row.photo.description)" :key="index">
              <button
                v-if="part.type === 'friend'"
                type="button"
                class="description-friend"
                @click="applyFriendFilter(part.id)"
              >
                {{ part.name }}
              </button>
              <template v-else>{{ part.text }}</template>
            </template>
          </p>

          <div v-if="friendList(entry.row.photo).length" class="friend-row" aria-label="Friends in this photo">
            <span>With</span>
            <button
              v-for="friend in friendList(entry.row.photo)"
              :key="friend.id"
              type="button"
              @click="applyFriendFilter(friend.id)"
            >
              {{ friend.name }}
            </button>
          </div>
        </div>

        <section v-if="entry.row.linkedPhotos.length" class="linked-photos" aria-label="Linked moments">
          <div class="linked-grid">
            <button
              v-for="linkedPhoto in entry.row.linkedPhotos"
              :key="linkedPhoto.id"
              class="linked-trigger"
              type="button"
              :aria-label="`Open ${linkedPhoto.filename}`"
              @click="openPhoto(linkedPhoto.id)"
            >
              <LazyPhoto :src="thumbnailPath(linkedPhoto.filename)" :alt="linkedPhoto.description || linkedPhoto.filename" />
              <span class="linked-caption">
                <span>{{ formatLinkedDate(linkedPhoto, entry.row.photo) }}</span>
                <span class="linked-number">#{{ linkedPhoto.id }}</span>
                <span v-if="hasWorld(linkedPhoto) && linkedPhoto.world !== entry.row.photo.world" class="linked-world">
                  {{ worldFor(linkedPhoto).name }}
                </span>
              </span>
            </button>
          </div>
        </section>
      </article>
      </div>
    </section>
  </main>

  <footer class="site-footer">
    <p>{{ imageCount }} photos · {{ outingCount }} outings</p>
    <p>{{ daysInVrchat }} days since Mars joined VRChat</p>
  </footer>

  <Teleport to="body">
    <div v-if="activePhoto" class="lightbox" role="dialog" aria-modal="true" @click.self="closeLightbox">
      <button class="lightbox-button lightbox-close" type="button" aria-label="Close" @click="closeLightbox">
        x
      </button>
      <button class="lightbox-button lightbox-prev" type="button" aria-label="Previous photo" @click="showPreviousPhoto">
        &lt;
      </button>
      <button class="lightbox-button lightbox-next" type="button" aria-label="Next photo" @click="showNextPhoto">
        &gt;
      </button>

      <figure class="lightbox-panel">
        <div class="lightbox-toolbar">
          <span>{{ activePosition }} / {{ lightboxPhotos.length }}</span>
          <label class="zoom-slider">
            <span>Zoom {{ zoomLabel }}</span>
            <input v-model.number="zoomLevel" type="range" min="1" max="2.5" step="0.1" aria-label="Zoom" />
          </label>
        </div>

        <div ref="lightboxStage" class="lightbox-stage">
          <div class="lightbox-zoom-surface" :style="zoomSurfaceStyle">
            <img
              class="lightbox-image"
              :src="photoPath(activePhoto.filename)"
              :alt="activePhoto.description || activePhoto.filename"
            />
          </div>
        </div>

        <figcaption class="lightbox-caption">
          <div>
            <span>#{{ activePhoto.id }}</span>
            <time :datetime="activePhoto.captured">{{ formatGalleryDate(activePhoto.captured) }}</time>
            <button v-if="hasWorld(activePhoto)" type="button" @click="applyWorldFilter(activePhoto.world, true)">
              {{ worldFor(activePhoto).name }}
            </button>
          </div>
          <p v-if="hasDescription(activePhoto)">
            <template v-for="(part, index) in descriptionParts(activePhoto.description)" :key="index">
              <button
                v-if="part.type === 'friend'"
                type="button"
                class="description-friend"
                @click="applyFriendFilter(part.id, true)"
              >
                {{ part.name }}
              </button>
              <template v-else>{{ part.text }}</template>
            </template>
          </p>
          <p v-if="friendList(activePhoto).length" class="caption-friends">
            With
            <button
              v-for="friend in friendList(activePhoto)"
              :key="friend.id"
              type="button"
              @click="applyFriendFilter(friend.id, true)"
            >
              {{ friend.name }}
            </button>
          </p>
        </figcaption>
      </figure>
    </div>
  </Teleport>
</template>
