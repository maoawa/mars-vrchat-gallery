<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import LazyPhoto from './components/LazyPhoto.vue'
import friendsData from './data/friends.json'
import imagesData from './data/images.json'
import worldsData from './data/worlds.json'
import { detectPreferredLanguage, languageCopy, type Language } from './i18n'
import { icons, type Icon } from './icons'
import type { Friend, GalleryImage, GalleryRow, World } from './types'
import { parseAsGalleryDate } from './utils/date'
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
type DescriptionPart =
  | { type: 'text'; text: string }
  | { type: 'emphasis'; text: string }
  | { type: 'friend'; id: string; name: string }

const friends = friendsData as Friend[]
const worlds = worldsData as World[]
const photos = [...(imagesData as GalleryImage[])].sort((a, b) => b.captured.localeCompare(a.captured))

const friendsById = new Map(friends.map((friend) => [friend.id, friend]))
const worldsById = new Map(worlds.map((world) => [world.id, world]))
const photosById = new Map(photos.map((photo) => [photo.id, photo]))
const socialLinks: Array<{ label: string; icon: Icon; href: string }> = [
  { label: 'GitHub', icon: 'github', href: 'https://github.com/maoawa/mars-vrchat-gallery' },
  { label: 'X', icon: 'x', href: 'https://twitter.com/winmemzqwq' },
  { label: 'Telegram', icon: 'telegram', href: 'https://t.me/maoawa' },
  { label: 'Discord', icon: 'discord', href: 'https://discord.com/users/742704239410675725' },
  { label: 'Facebook', icon: 'facebook', href: 'https://www.facebook.com/profile.php?id=100088742570811' },
  { label: 'Instagram', icon: 'instagram', href: 'https://www.instagram.com/winmemzqwq' },
  { label: 'Email', icon: 'email', href: 'mailto:winmemzqwq@gmail.com' },
]
const allGalleryRows: GalleryRow[] = photos
  .filter((photo) => !photo.parent)
  .map((photo) => ({
    photo,
    linkedPhotos: (photo.linked ?? [])
      .map((linkedPhotoId) => photosById.get(linkedPhotoId))
      .filter((linkedPhoto): linkedPhoto is GalleryImage => Boolean(linkedPhoto)),
  }))

const now = ref(Date.now())
const currentLanguage = ref<Language>(detectPreferredLanguage())
const activeIndex = ref<number | null>(null)
const activePhotoList = ref<GalleryImage[] | null>(null)
const zoomLevel = ref(1)
const activeFilter = ref<GalleryFilter | null>(null)
const galleryColumnCount = ref(1)
const lightboxStage = ref<HTMLElement | null>(null)
const activeQrContactId = ref<'wechat' | 'qq' | null>(null)

let clockTimer: number | undefined

const copy = computed(() => languageCopy[currentLanguage.value])
const contactButtons = computed(() => [
  {
    id: 'wechat' as const,
    label: copy.value.wechat,
    icon: 'wechat' as Icon,
    number: '12133206888',
    qrPath: '/wechat-qr.jpg',
  },
  {
    id: 'qq' as const,
    label: copy.value.qq,
    icon: 'qq' as Icon,
    number: '1874985948',
    qrPath: '/qq-qr.jpg',
  },
])

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
const randomOuting = ref<GalleryRow | null>(
  allGalleryRows.length ? allGalleryRows[Math.floor(Math.random() * allGalleryRows.length)] : null,
)
const randomOutingPhotos = computed(() =>
  randomOuting.value ? [randomOuting.value.photo, ...randomOuting.value.linkedPhotos] : [],
)
const currentLightboxPhotos = computed(() => activePhotoList.value ?? lightboxPhotos.value)
const activeQrContact = computed(
  () => contactButtons.value.find((contact) => contact.id === activeQrContactId.value) ?? null,
)
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

  return currentLightboxPhotos.value[activeIndex.value] ?? null
})

const activePosition = computed(() => (activeIndex.value === null ? 0 : activeIndex.value + 1))
const daysInVrchat = computed(() => daysSinceVrchatStart(now.value))
const imageCount = computed(() => photos.length)
const outingCount = computed(() => allGalleryRows.length)
const filteredOutingCount = computed(() => galleryRows.value.length)
const zoomLabel = computed(() => `${Math.round(zoomLevel.value * 100)}%`)
const footerSummary = computed(() => {
  if (currentLanguage.value === 'zh') {
    return `${imageCount.value} ${copy.value.photos} · ${outingCount.value} ${copy.value.outings}`
  }

  return `${imageCount.value} photos · ${outingCount.value} outings`
})
const footerDays = computed(() => {
  return `${copy.value.footerDaysBefore}${daysInVrchat.value}${copy.value.footerDaysAfter}`
})

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

function hasWorld(photo: GalleryImage) {
  return photo.world.trim().length > 0
}

function localisedText(en?: string, zh?: string) {
  const enText = typeof en === 'string' ? en : ''
  const zhText = typeof zh === 'string' ? zh : ''

  return currentLanguage.value === 'zh' ? zhText.trim() || enText : enText.trim() || zhText
}

function worldName(worldId: string) {
  const world = worldsById.get(worldId)
  return world ? localisedText(world.name_en, world.name_zh) : worldId
}

function friendName(friendId: string) {
  const friend = friendsById.get(friendId)
  return friend ? localisedText(friend.name_en, friend.name_zh) : friendId
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
  return photoDescription(photo).trim().length > 0
}

function photoDescription(photo: GalleryImage) {
  return localisedText(photo.description_en, photo.description_zh)
}

function photoAlt(photo: GalleryImage) {
  return photoDescription(photo) || photo.filename
}

function descriptionParts(description: string) {
  const parts: DescriptionPart[] = []
  const friendReferencePattern = /\[\[([a-zA-Z0-9_-]+)\]\]/g
  const emphasisPattern = /\*([^*\n]+)\*/g
  let cursor = 0

  while (cursor < description.length) {
    friendReferencePattern.lastIndex = cursor
    emphasisPattern.lastIndex = cursor

    const friendMatch = friendReferencePattern.exec(description)
    const emphasisMatch = emphasisPattern.exec(description)
    const nextMatch =
      friendMatch && (!emphasisMatch || friendMatch.index <= emphasisMatch.index) ? friendMatch : emphasisMatch

    if (!nextMatch) {
      parts.push({ type: 'text', text: description.slice(cursor) })
      break
    }

    if (nextMatch.index > cursor) {
      parts.push({ type: 'text', text: description.slice(cursor, nextMatch.index) })
    }

    if (nextMatch === friendMatch) {
      parts.push({
        type: 'friend',
        id: nextMatch[1],
        name: friendName(nextMatch[1]),
      })
    } else {
      parts.push({ type: 'emphasis', text: nextMatch[1] })
    }

    cursor = nextMatch.index + nextMatch[0].length
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
  activePhotoList.value = null
}

function formatLinkedDate(photo: GalleryImage, parentPhoto: GalleryImage) {
  return isSameGalleryDay(photo, parentPhoto) ? formatTime(photo.captured) : formatDate(photo.captured)
}

function isSameGalleryDay(photo: GalleryImage, parentPhoto: GalleryImage) {
  const photoDate = parseAsGalleryDate(photo.captured)
  const parentDate = parseAsGalleryDate(parentPhoto.captured)

  return photoDate.toDateString() === parentDate.toDateString()
}

function formatTime(capturedAt: string) {
  const date = parseAsGalleryDate(capturedAt)
  const hours = date.getHours()
  const minutes = date.getMinutes()

  if (currentLanguage.value === 'zh') {
    const meridiem = hours >= 12 ? '下午' : '上午'
    const hour12 = hours % 12 || 12

    return `${meridiem}${hour12}:${String(minutes).padStart(2, '0')}`
  }

  const meridiem = hours >= 12 ? 'PM' : 'AM'
  const hour12 = hours % 12 || 12

  return `${hour12}:${String(minutes).padStart(2, '0')} ${meridiem}`
}

function formatDate(capturedAt: string) {
  return formatGalleryDate(capturedAt, currentLanguage.value)
}

function toggleLanguage() {
  currentLanguage.value = currentLanguage.value === 'en' ? 'zh' : 'en'
}

function openQrContact(contactId: 'wechat' | 'qq') {
  activeQrContactId.value = contactId
}

function closeQrContact() {
  activeQrContactId.value = null
}

function openPhoto(photoId: number, sourcePhotos = lightboxPhotos.value) {
  const index = sourcePhotos.findIndex((photo) => photo.id === photoId)

  if (index >= 0) {
    activePhotoList.value = sourcePhotos
    activeIndex.value = index
    zoomLevel.value = 1
  }
}

function closeLightbox() {
  activeIndex.value = null
  activePhotoList.value = null
  zoomLevel.value = 1
}

function showPreviousPhoto() {
  if (activeIndex.value === null || !currentLightboxPhotos.value.length) {
    return
  }

  activeIndex.value =
    (activeIndex.value - 1 + currentLightboxPhotos.value.length) % currentLightboxPhotos.value.length
  zoomLevel.value = 1
}

function showNextPhoto() {
  if (activeIndex.value === null || !currentLightboxPhotos.value.length) {
    return
  }

  activeIndex.value = (activeIndex.value + 1) % currentLightboxPhotos.value.length
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
  if (activeQrContact.value && event.key === 'Escape') {
    closeQrContact()
    return
  }

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

watch([activePhoto, activeQrContact], ([photo, qrContact]) => {
  document.body.classList.toggle('lightbox-open', Boolean(photo) || Boolean(qrContact))

  if (photo) {
    nextTick(centreZoomStage)
  }
})

watch(zoomLevel, () => {
  if (activePhoto.value) {
    nextTick(centreZoomStage)
  }
})

watch(
  currentLanguage,
  (language) => {
    document.documentElement.lang = language === 'zh' ? 'zh-CN' : 'en-GB'
    window.localStorage.setItem('gallery-language', language)
  },
  { immediate: true },
)

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
    <div class="language-switch">
      <button type="button" :aria-label="copy.languageLabel" @click="toggleLanguage">
        {{ copy.languageToggle }}
      </button>
    </div>

    <header class="site-header">
      <h1>{{ copy.title }}</h1>
      <p class="lede" :class="{ 'lede-cn': currentLanguage === 'zh' }">
        {{ copy.introBeforeLink }}
        <a href="https://maao.cc/" target="_blank" rel="noreferrer">maao.cc</a>
        {{ copy.introAfterLink }}
      </p>
    </header>

    <section v-if="randomOuting" class="random-outing" aria-label="Random outing">
      <div class="random-outing__header">
        <p>{{ copy.randomMemory }}</p>
      </div>

      <article class="random-outing__card">
        <button
          class="random-outing__image"
          type="button"
          :aria-label="`${copy.open} ${randomOuting.photo.filename}`"
          @click="openPhoto(randomOuting.photo.id, randomOutingPhotos)"
        >
          <LazyPhoto :src="thumbnailPath(randomOuting.photo.filename)" :alt="photoAlt(randomOuting.photo)" />
        </button>

        <div class="random-outing__body">
          <div class="photo-kicker">
            <span class="photo-number">#{{ randomOuting.photo.id }}</span>
            <time :datetime="randomOuting.photo.captured">{{ formatDate(randomOuting.photo.captured) }}</time>
            <button
              v-if="hasWorld(randomOuting.photo)"
              class="world-link"
              type="button"
              @click="applyWorldFilter(randomOuting.photo.world)"
            >
              <svg aria-hidden="true" class="world-pin" :viewBox="icons.pin.viewBox">
                <path v-for="path in icons.pin.paths" :key="path" :d="path" />
              </svg>
              <span>{{ worldName(randomOuting.photo.world) }}</span>
            </button>
          </div>

          <p v-if="hasDescription(randomOuting.photo)" class="photo-description">
            <template v-for="(part, index) in descriptionParts(photoDescription(randomOuting.photo))" :key="index">
              <button
                v-if="part.type === 'friend'"
                type="button"
                class="description-friend"
                @click="applyFriendFilter(part.id)"
              >
                {{ part.name }}
              </button>
              <em v-else-if="part.type === 'emphasis'">{{ part.text }}</em>
              <template v-else>{{ part.text }}</template>
            </template>
          </p>

          <div v-if="friendList(randomOuting.photo).length" class="friend-row" aria-label="Friends in this outing">
            <span>{{ copy.with }}</span>
            <button
              v-for="friend in friendList(randomOuting.photo)"
              :key="friend.id"
              type="button"
              @click="applyFriendFilter(friend.id)"
            >
              {{ friend.name }}
            </button>
          </div>

          <div v-if="randomOuting.linkedPhotos.length" class="random-outing__linked">
            <button
              v-for="linkedPhoto in randomOuting.linkedPhotos"
              :key="linkedPhoto.id"
              type="button"
              :aria-label="`${copy.open} ${linkedPhoto.filename}`"
              @click="openPhoto(linkedPhoto.id, randomOutingPhotos)"
            >
              <LazyPhoto :src="thumbnailPath(linkedPhoto.filename)" :alt="photoAlt(linkedPhoto)" />
              <span>#{{ linkedPhoto.id }}</span>
            </button>
          </div>
        </div>
      </article>
    </section>

    <div class="section-divider" aria-hidden="true"></div>

    <section v-if="activeFilter" class="filter-strip" aria-live="polite">
      <p>
        {{ copy.showing }} {{ filteredOutingCount }}
        {{ filteredOutingCount === 1 ? copy.outing : copy.outings }} {{ copy.for }}
        <span>{{ activeFilterLabel }}</span>
      </p>
      <button type="button" @click="clearFilter">{{ copy.clear }}</button>
    </section>

    <section class="gallery" aria-label="VRChat photos">
      <div v-for="(column, columnIndex) in galleryColumns" :key="columnIndex" class="gallery-column">
      <article v-for="entry in column" :key="entry.row.photo.id" class="photo-card">
        <button
          class="photo-trigger"
          type="button"
          :aria-label="`${copy.open} ${entry.row.photo.filename}`"
          @click="openPhoto(entry.row.photo.id)"
        >
          <LazyPhoto
            :src="thumbnailPath(entry.row.photo.filename)"
            :alt="photoAlt(entry.row.photo)"
            :eager="entry.index === 0"
          />
        </button>

        <div class="photo-body">
          <div class="photo-kicker">
            <span class="photo-number">#{{ entry.row.photo.id }}</span>
            <time :datetime="entry.row.photo.captured">{{ formatDate(entry.row.photo.captured) }}</time>
            <button
              v-if="hasWorld(entry.row.photo)"
              class="world-link"
              type="button"
              @click="applyWorldFilter(entry.row.photo.world)"
            >
              <svg aria-hidden="true" class="world-pin" :viewBox="icons.pin.viewBox">
                <path v-for="path in icons.pin.paths" :key="path" :d="path" />
              </svg>
              <span>{{ worldName(entry.row.photo.world) }}</span>
            </button>
          </div>

          <p v-if="hasDescription(entry.row.photo)" class="photo-description">
            <template v-for="(part, index) in descriptionParts(photoDescription(entry.row.photo))" :key="index">
              <button
                v-if="part.type === 'friend'"
                type="button"
                class="description-friend"
                @click="applyFriendFilter(part.id)"
              >
                {{ part.name }}
              </button>
              <em v-else-if="part.type === 'emphasis'">{{ part.text }}</em>
              <template v-else>{{ part.text }}</template>
            </template>
          </p>

          <div v-if="friendList(entry.row.photo).length" class="friend-row" aria-label="Friends in this photo">
            <span>{{ copy.with }}</span>
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
              :aria-label="`${copy.open} ${linkedPhoto.filename}`"
              @click="openPhoto(linkedPhoto.id)"
            >
              <LazyPhoto :src="thumbnailPath(linkedPhoto.filename)" :alt="photoAlt(linkedPhoto)" />
              <span class="linked-caption">
                <span>{{ formatLinkedDate(linkedPhoto, entry.row.photo) }}</span>
                <span class="linked-number">#{{ linkedPhoto.id }}</span>
                <span v-if="hasWorld(linkedPhoto) && linkedPhoto.world !== entry.row.photo.world" class="linked-world">
                  <svg aria-hidden="true" class="world-pin" :viewBox="icons.pin.viewBox">
                    <path v-for="path in icons.pin.paths" :key="path" :d="path" />
                  </svg>
                  <span>{{ worldName(linkedPhoto.world) }}</span>
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
    <div class="footer-stats">
      <p>{{ footerSummary }}</p>
      <p>{{ footerDays }}</p>
    </div>

    <nav class="footer-social" aria-label="Social links">
      <a
        v-for="link in socialLinks"
        :key="link.label"
        :href="link.href"
        :aria-label="link.label"
        target="_blank"
        rel="noreferrer"
      >
        <svg aria-hidden="true" class="social-icon" :viewBox="icons[link.icon].viewBox">
          <path v-for="path in icons[link.icon].paths" :key="path" :d="path" />
        </svg>
      </a>

      <button
        v-for="contact in contactButtons"
        :key="contact.id"
        type="button"
        :aria-label="contact.label"
        @click="openQrContact(contact.id)"
      >
        <svg aria-hidden="true" class="social-icon" :viewBox="icons[contact.icon].viewBox">
          <path v-for="path in icons[contact.icon].paths" :key="path" :d="path" />
        </svg>
      </button>
    </nav>

    <div class="footer-contact">
      <p>{{ copy.copyright }}</p>
    </div>
  </footer>

  <Teleport to="body">
    <div v-if="activeQrContact" class="qr-modal" role="dialog" aria-modal="true" @click.self="closeQrContact">
      <section class="qr-panel" :aria-label="activeQrContact.label">
        <button class="qr-close" type="button" :aria-label="copy.close" @click="closeQrContact">x</button>
        <img class="qr-image" :src="activeQrContact.qrPath" :alt="`${activeQrContact.label} QR code`" />
        <div class="qr-caption">
          <p>{{ activeQrContact.label }}</p>
          <strong>{{ activeQrContact.number }}</strong>
        </div>
      </section>
    </div>

    <div v-if="activePhoto" class="lightbox" role="dialog" aria-modal="true" @click.self="closeLightbox">
      <button class="lightbox-button lightbox-close" type="button" :aria-label="copy.close" @click="closeLightbox">
        x
      </button>
      <button class="lightbox-button lightbox-prev" type="button" :aria-label="copy.previous" @click="showPreviousPhoto">
        &lt;
      </button>
      <button class="lightbox-button lightbox-next" type="button" :aria-label="copy.next" @click="showNextPhoto">
        &gt;
      </button>

      <figure class="lightbox-panel">
        <div class="lightbox-toolbar">
          <span>{{ activePosition }} / {{ currentLightboxPhotos.length }}</span>
          <label class="zoom-slider">
            <span>{{ copy.zoom }} {{ zoomLabel }}</span>
            <input v-model.number="zoomLevel" type="range" min="1" max="2.5" step="0.1" :aria-label="copy.zoom" />
          </label>
        </div>

        <div ref="lightboxStage" class="lightbox-stage">
          <div class="lightbox-zoom-surface" :style="zoomSurfaceStyle">
            <img
              class="lightbox-image"
              :src="photoPath(activePhoto.filename)"
              :alt="photoAlt(activePhoto)"
            />
          </div>
        </div>

        <figcaption class="lightbox-caption">
          <div>
            <span>#{{ activePhoto.id }}</span>
            <time :datetime="activePhoto.captured">{{ formatDate(activePhoto.captured) }}</time>
            <button
              v-if="hasWorld(activePhoto)"
              class="world-link"
              type="button"
              @click="applyWorldFilter(activePhoto.world, true)"
            >
              <svg aria-hidden="true" class="world-pin" :viewBox="icons.pin.viewBox">
                <path v-for="path in icons.pin.paths" :key="path" :d="path" />
              </svg>
              <span>{{ worldName(activePhoto.world) }}</span>
            </button>
          </div>
          <p v-if="hasDescription(activePhoto)">
            <template v-for="(part, index) in descriptionParts(photoDescription(activePhoto))" :key="index">
              <button
                v-if="part.type === 'friend'"
                type="button"
                class="description-friend"
                @click="applyFriendFilter(part.id, true)"
              >
                {{ part.name }}
              </button>
              <em v-else-if="part.type === 'emphasis'">{{ part.text }}</em>
              <template v-else>{{ part.text }}</template>
            </template>
          </p>
          <p v-if="friendList(activePhoto).length" class="caption-friends">
            {{ copy.with }}
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
