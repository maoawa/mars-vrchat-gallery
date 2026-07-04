<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import LazyPhoto from './components/LazyPhoto.vue'
import friendsData from './data/friends.json'
import imagesData from './data/images.json'
import specialEventsData from './data/special-events.json'
import tagsData from './data/tags.json'
import worldsData from './data/worlds.json'
import { detectPreferredLanguage, languageCopy, type Language } from './i18n'
import { icons, type Icon } from './icons'
import type { Friend, GalleryImage, GalleryRow, PhotoTag, PhotoTagGroup, SpecialEvent, World } from './types'
import { parseAsGalleryDate } from './utils/date'
import { daysSinceVrchatStart, formatGalleryDate, photoPath, thumbnailPath } from './utils/gallery'

declare global {
  interface Window {
    tagsEdit?: {
      on: () => void
      off: () => void
      print: () => string
      save: () => Promise<string>
    }
  }
}

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
  | { type: 'break' }
  | { type: 'emphasis'; text: string }
  | { type: 'friend'; id: string; name: string }
  | { type: 'world'; id: string; name: string }
type SpecialEventView = SpecialEvent & {
  photos: GalleryImage[]
  featuredPhotos: GalleryImage[]
  linkedPhotos: GalleryImage[]
  sortKey: string
}
type GalleryFlowItem =
  | {
      type: 'gallery'
      id: string
      columns: Array<Array<{ row: GalleryRow; index: number }>>
      rowCount: number
    }
  | {
      type: 'special-event'
      id: string
      event: SpecialEventView
    }
type ResolvedPhotoTag = {
  friendId: string
  index: number
  name: string
  x: number
  y: number
  position: 'top' | 'right' | 'bottom' | 'left'
}
type DraggedPhotoTag = {
  photoId: number
  tagIndex: number
  pointerId: number
}

const monthNames = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
]
const friends = friendsData as Friend[]
const worlds = worldsData as World[]
const photos = [...(imagesData as GalleryImage[])].sort((a, b) => b.captured.localeCompare(a.captured))
const specialEventRecords = specialEventsData as SpecialEvent[]
const photoTagRecords = tagsData as PhotoTagGroup[]

const friendsById = new Map(friends.map((friend) => [friend.id, friend]))
const worldsById = new Map(worlds.map((world) => [world.id, world]))
const photosById = new Map(photos.map((photo) => [photo.id, photo]))
const editableTagsByPhotoId = new Map(
  photoTagRecords.map((record) => [
    record.photo,
    record.tags.map((tag) => ({ ...tag })),
  ]),
)
const socialLinks: Array<{ label: string; icon: Icon; href: string }> = [
  { label: 'GitHub', icon: 'github', href: 'https://github.com/maoawa/mars-vrchat-gallery' },
  { label: 'X', icon: 'x', href: 'https://twitter.com/winmemzqwq' },
  { label: 'Telegram', icon: 'telegram', href: 'https://t.me/maoawa' },
  { label: 'Discord', icon: 'discord', href: 'https://discord.com/users/742704239410675725' },
  { label: 'Facebook', icon: 'facebook', href: 'https://www.facebook.com/profile.php?id=100088742570811' },
  { label: 'Instagram', icon: 'instagram', href: 'https://www.instagram.com/winmemzqwq' },
  { label: 'Email', icon: 'email', href: 'mailto:winmemzqwq@gmail.com' },
]
const specialEvents: SpecialEventView[] = specialEventRecords
  .map((event) => {
    const eventPhotos = event.photo_ids
      .map((photoId) => photosById.get(photoId))
      .filter((photo): photo is GalleryImage => Boolean(photo))
    const featuredPhotos = event.featured_photo_ids
      .map((photoId) => photosById.get(photoId))
      .filter((photo): photo is GalleryImage => Boolean(photo))
    const featuredPhotoIds = new Set(featuredPhotos.map((photo) => photo.id))

    return {
      ...event,
      photos: eventPhotos,
      featuredPhotos,
      linkedPhotos: eventPhotos.filter((photo) => !featuredPhotoIds.has(photo.id)),
      sortKey: eventPhotos.reduce(
        (latestCaptured, photo) => (photo.captured > latestCaptured ? photo.captured : latestCaptured),
        '',
      ),
    }
  })
  .filter((event) => event.photos.length > 0 && event.featuredPhotos.length > 0)
  .sort((a, b) => b.sortKey.localeCompare(a.sortKey))
const allGalleryRows: GalleryRow[] = photos
  .filter((photo) => !photo.parent && !photo['special-events'])
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
const activeFilter = ref<GalleryFilter | null>(null)
const galleryColumnCount = ref(1)
const lightboxStage = ref<HTMLElement | null>(null)
const lightboxZoomSurface = ref<HTMLElement | null>(null)
const activeQrContactId = ref<'wechat' | 'qq' | null>(null)
const highlightedPhotoId = ref<number | null>(null)
const highlightedSpecialEventId = ref<string | null>(null)

const minZoom = 1
const maxZoom = 4
const zoomStep = 0.25
const doubleClickZoom = 2.5
const swipeThreshold = 72
const swipeAnimationDuration = 180
const lightboxTagsVisibleStorageKey = 'gallery-lightbox-tags-visible'
const tagsToggleTutorialStorageKey = 'gallery-tags-toggle-tutorial-complete'

const zoomLevel = ref(1)
const isDragging = ref(false)
const isPinching = ref(false)
const isSwiping = ref(false)
const isSwipeAnimating = ref(false)
const lightboxControlsVisible = ref(true)
const lightboxTagsVisible = ref(true)
const lightboxTagsToggleTutorialVisible = ref(false)
const activeImageNaturalSize = ref<{ width: number; height: number } | null>(null)
const zoomSurfaceSize = ref({ width: 0, height: 0 })
const swipeOffsetX = ref(0)
const tagEditingEnabled = ref(false)
const tagEditVersion = ref(0)
const draggedPhotoTag = ref<DraggedPhotoTag | null>(null)

let startClientX = 0
let startClientY = 0
let lastClientX = 0
let lastClientY = 0
let startScrollLeft = 0
let startScrollTop = 0
let pinchStartDistance = 0
let pinchStartZoom = 1
let hasMovedInGesture = false
let suppressNextClick = false
let clickToggleTimer: number | undefined
let lightboxZoomSurfaceObserver: ResizeObserver | undefined
let tagsToggleTutorialTimer: number | undefined
let swipeAnimationTimer: number | undefined

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

const filteredSpecialEvents = computed(() => {
  if (!activeFilter.value) {
    return specialEvents
  }

  return specialEvents.filter((event) => specialEventMatchesFilter(event, activeFilter.value))
})

const gallerySections = computed(() => {
  if (!filteredSpecialEvents.value.length) {
    return [
      {
        type: 'gallery' as const,
        id: 'all',
        columns: buildGalleryColumns(galleryRows.value),
        rowCount: galleryRows.value.length,
      },
    ]
  }

  const flowItems: GalleryFlowItem[] = []
  let rowCursor = 0

  filteredSpecialEvents.value.forEach((event) => {
    const rowsBeforeEvent: GalleryRow[] = []

    while (
      rowCursor < galleryRows.value.length &&
      galleryRows.value[rowCursor].photo.captured > event.sortKey
    ) {
      rowsBeforeEvent.push(galleryRows.value[rowCursor])
      rowCursor += 1
    }

    if (rowsBeforeEvent.length) {
      flowItems.push({
        type: 'gallery',
        id: `gallery-before-${event.id}`,
        columns: buildGalleryColumns(rowsBeforeEvent),
        rowCount: rowsBeforeEvent.length,
      })
    }

    flowItems.push({
      type: 'special-event',
      id: `special-event-${event.id}`,
      event,
    })
  })

  const remainingRows = galleryRows.value.slice(rowCursor)

  if (remainingRows.length) {
    flowItems.push({
      type: 'gallery',
      id: 'gallery-after-special-events',
      columns: buildGalleryColumns(remainingRows),
      rowCount: remainingRows.length,
    })
  }

  return flowItems
})

const lightboxPhotos = computed(() =>
  gallerySections.value.flatMap((item) => {
    if (item.type === 'special-event') {
      return item.event.photos
    }

    return item.columns
      .flat()
      .sort((a, b) => a.index - b.index)
      .flatMap((entry) => [entry.row.photo, ...entry.row.linkedPhotos])
  }),
)
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
function buildGalleryColumns(rows: GalleryRow[]) {
  const columns: Array<Array<{ row: GalleryRow; index: number }>> = Array.from(
    { length: galleryColumnCount.value },
    () => [],
  )

  rows.forEach((row, index) => {
    columns[index % galleryColumnCount.value].push({ row, index })
  })

  return columns
}

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
const filteredOutingCount = computed(() => galleryRows.value.length + filteredSpecialEvents.value.length)
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

const lightboxImageStyle = computed(() => {
  if (zoomLevel.value <= 1) {
    return {
      cursor: 'zoom-in',
    }
  }

  return {
    cursor: isDragging.value ? 'grabbing' : 'grab',
  }
})
const lightboxImageFrameStyle = computed(() => {
  const naturalSize = activeImageNaturalSize.value
  const surfaceSize = zoomSurfaceSize.value

  if (!naturalSize || !surfaceSize.width || !surfaceSize.height) {
    return {
      width: '100%',
      height: '100%',
      '--lightbox-swipe-offset': `${swipeOffsetX.value}px`,
    }
  }

  const imageRatio = naturalSize.width / naturalSize.height
  const surfaceRatio = surfaceSize.width / surfaceSize.height
  const width = imageRatio >= surfaceRatio ? surfaceSize.width : surfaceSize.height * imageRatio
  const height = imageRatio >= surfaceRatio ? surfaceSize.width / imageRatio : surfaceSize.height

  return {
    width: `${width}px`,
    height: `${height}px`,
    '--lightbox-swipe-offset': `${swipeOffsetX.value}px`,
  }
})
const activePhotoTags = computed(() => {
  if (!activePhoto.value) {
    return []
  }

  return photoTagList(activePhoto.value)
})

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

function photoTagList(photo: GalleryImage): ResolvedPhotoTag[] {
  tagEditVersion.value

  return (editableTagsByPhotoId.get(photo.id) ?? [])
    .filter((tag) => tag.friend.trim().length > 0)
    .map((tag, index) => ({
      friendId: tag.friend,
      index,
      name: friendName(tag.friend),
      x: clampPercent(tag.x),
      y: clampPercent(tag.y),
      position: tag.position ?? 'bottom',
    }))
}

function clampPercent(value: number) {
  if (!Number.isFinite(value)) {
    return 50
  }

  return Math.min(100, Math.max(0, value))
}

function photoTagStyle(tag: ResolvedPhotoTag) {
  return {
    left: `${tag.x}%`,
    top: `${tag.y}%`,
  }
}

function photoTagClass(tag: ResolvedPhotoTag) {
  return `is-label-${tag.position}`
}

function tagCoordinatesFromClientPoint(clientX: number, clientY: number) {
  const frame = lightboxZoomSurface.value?.querySelector<HTMLElement>('.lightbox-image-frame')

  if (!frame || !activeImageNaturalSize.value) {
    return null
  }

  const rect = frame.getBoundingClientRect()

  if (!rect.width || !rect.height) {
    return null
  }

  return {
    x: Number(clampPercent(((clientX - rect.left) / rect.width) * 100).toFixed(1)),
    y: Number(clampPercent(((clientY - rect.top) / rect.height) * 100).toFixed(1)),
  }
}

function eventFriendList(event: SpecialEventView) {
  return (event.friends ?? [])
    .filter((friendId) => friendId.trim().length > 0)
    .map((friendId) => ({
      id: friendId,
      name: friendName(friendId),
    }))
}

function hasEventWorld(event: SpecialEventView) {
  return Boolean(event.world?.trim())
}

function shouldShowEventPhotoWorld(photo: GalleryImage, event: SpecialEventView) {
  return hasWorld(photo) && photo.world !== event.world
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
  const friendPattern = /\[\[([a-zA-Z0-9_-]+)\]\]/g
  const worldPattern = /\{\{([a-zA-Z0-9_.-]+)\}\}/g
  const emphasisPattern = /\*([^*\n]+)\*/g
  const breakPattern = /<br\s*\/?>/gi
  let cursor = 0

  while (cursor < description.length) {
    friendPattern.lastIndex = cursor
    worldPattern.lastIndex = cursor
    emphasisPattern.lastIndex = cursor
    breakPattern.lastIndex = cursor

    const friendMatch = friendPattern.exec(description)
    const worldMatch = worldPattern.exec(description)
    const emphasisMatch = emphasisPattern.exec(description)
    const breakMatch = breakPattern.exec(description)
    const matches = [
      friendMatch ? { kind: 'friend' as const, match: friendMatch } : null,
      worldMatch ? { kind: 'world' as const, match: worldMatch } : null,
      emphasisMatch ? { kind: 'emphasis' as const, match: emphasisMatch } : null,
      breakMatch ? { kind: 'break' as const, match: breakMatch } : null,
    ].filter((item): item is NonNullable<typeof item> => Boolean(item))
    const nextMatch = matches.sort((a, b) => a.match.index - b.match.index)[0]

    if (!nextMatch) {
      parts.push({ type: 'text', text: description.slice(cursor) })
      break
    }

    if (nextMatch.match.index > cursor) {
      parts.push({ type: 'text', text: description.slice(cursor, nextMatch.match.index) })
    }

    if (nextMatch.kind === 'friend') {
      parts.push({
        type: 'friend',
        id: nextMatch.match[1],
        name: friendName(nextMatch.match[1]),
      })
    } else if (nextMatch.kind === 'world') {
      const worldId = nextMatch.match[1]

      parts.push(
        worldsById.has(worldId)
          ? {
              type: 'world',
              id: worldId,
              name: worldName(worldId),
            }
          : { type: 'text', text: nextMatch.match[0] },
      )
    } else if (nextMatch.kind === 'emphasis') {
      parts.push({
        type: 'emphasis',
        text: nextMatch.match[1],
      })
    } else {
      parts.push({ type: 'break' })
    }

    cursor = nextMatch.match.index + nextMatch.match[0].length
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

function specialEventMatchesFilter(event: SpecialEventView, filter: GalleryFilter | null) {
  if (!filter) {
    return true
  }

  if (filter.type === 'world') {
    return event.world === filter.id || event.photos.some((photo) => photoMatchesFilter(photo, filter))
  }

  return (event.friends ?? []).includes(filter.id) || event.photos.some((photo) => photoMatchesFilter(photo, filter))
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

function formatShortDateTime(capturedAt: string) {
  const date = parseAsGalleryDate(capturedAt)
  const hours = date.getHours()
  const minutes = date.getMinutes()

  if (currentLanguage.value === 'zh') {
    const meridiem = hours >= 12 ? '下午' : '上午'
    const hour12 = hours % 12 || 12

    return `${date.getMonth() + 1}月${date.getDate()}日 ${meridiem}${hour12}:${String(minutes).padStart(2, '0')}`
  }

  const meridiem = hours >= 12 ? 'PM' : 'AM'
  const hour12 = hours % 12 || 12

  return `${monthNames[date.getMonth()]} ${date.getDate()} at ${hour12}:${String(minutes).padStart(2, '0')} ${meridiem}`
}

function formatSpecialEventPhotoDate(photo: GalleryImage, event: SpecialEventView) {
  if (event.show_full_date) {
    return formatShortDateTime(photo.captured)
  }

  const firstPhoto = event.photos[0]

  return firstPhoto && isSameGalleryDay(photo, firstPhoto) ? formatTime(photo.captured) : formatShortDateTime(photo.captured)
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

function centreZoomStage() {
  const stage = lightboxStage.value

  if (!stage) {
    return
  }

  stage.scrollLeft = (stage.scrollWidth - stage.clientWidth) / 2
  stage.scrollTop = (stage.scrollHeight - stage.clientHeight) / 2
}

function updateZoomSurfaceSize() {
  const surface = lightboxZoomSurface.value

  if (!surface) {
    zoomSurfaceSize.value = { width: 0, height: 0 }
    return
  }

  const rect = surface.getBoundingClientRect()
  zoomSurfaceSize.value = {
    width: rect.width,
    height: rect.height,
  }
}

function handleLightboxImageLoad(event: Event) {
  const image = event.currentTarget as HTMLImageElement

  if (!image.naturalWidth || !image.naturalHeight) {
    return
  }

  activeImageNaturalSize.value = {
    width: image.naturalWidth,
    height: image.naturalHeight,
  }
  updateZoomSurfaceSize()
}

function resetZoom() {
  zoomLevel.value = 1
  isDragging.value = false
  isPinching.value = false
  isSwiping.value = false
  isSwipeAnimating.value = false
  swipeOffsetX.value = 0
  pinchStartDistance = 0
}

function clearPhotoClickTimer() {
  if (clickToggleTimer) {
    window.clearTimeout(clickToggleTimer)
    clickToggleTimer = undefined
  }
}

function clearSwipeAnimationTimer() {
  if (swipeAnimationTimer) {
    window.clearTimeout(swipeAnimationTimer)
    swipeAnimationTimer = undefined
  }
}

function hideLightboxControls() {
  lightboxControlsVisible.value = false
}

function resetLightboxViewState() {
  resetZoom()
  clearPhotoClickTimer()
  clearSwipeAnimationTimer()
  lightboxControlsVisible.value = true
  hasMovedInGesture = false
  suppressNextClick = false
}

function clampZoom(zoom: number) {
  return Math.min(maxZoom, Math.max(minZoom, zoom))
}

function resistedSwipeOffset(deltaX: number) {
  const maxOffset = Math.max(160, window.innerWidth * 0.42)
  const magnitude = Math.abs(deltaX)

  if (magnitude <= maxOffset) {
    return deltaX
  }

  const overflow = magnitude - maxOffset
  return Math.sign(deltaX) * (maxOffset + overflow * 0.22)
}

function settleSwipeOffset(offset: number, afterSettle?: () => void) {
  clearSwipeAnimationTimer()
  isSwipeAnimating.value = true
  swipeOffsetX.value = offset
  swipeAnimationTimer = window.setTimeout(() => {
    afterSettle?.()
    swipeOffsetX.value = 0
    isSwipeAnimating.value = false
    swipeAnimationTimer = undefined
  }, swipeAnimationDuration)
}

function zoomAtClientPoint(nextZoom: number, clientX: number, clientY: number) {
  const stage = lightboxStage.value
  const clampedZoom = clampZoom(nextZoom)

  if (!stage) {
    zoomLevel.value = clampedZoom
    return
  }

  const previousZoom = zoomLevel.value

  if (clampedZoom === previousZoom) {
    return
  }

  if (clampedZoom > minZoom) {
    hideLightboxControls()
  }

  const stageRect = stage.getBoundingClientRect()
  const viewportX = clientX - stageRect.left
  const viewportY = clientY - stageRect.top
  const anchorX = (stage.scrollLeft + viewportX) / previousZoom
  const anchorY = (stage.scrollTop + viewportY) / previousZoom

  zoomLevel.value = clampedZoom

  nextTick(() => {
    stage.scrollLeft = anchorX * clampedZoom - viewportX
    stage.scrollTop = anchorY * clampedZoom - viewportY

    if (clampedZoom === minZoom) {
      centreZoomStage()
    }
  })
}

function handleScrollZoom(event: WheelEvent) {
  const nextZoom = event.deltaY < 0 ? zoomLevel.value + zoomStep : zoomLevel.value - zoomStep

  zoomAtClientPoint(nextZoom, event.clientX, event.clientY)
}

function getTouchDistance(touches: TouchList) {
  const deltaX = touches[0].clientX - touches[1].clientX
  const deltaY = touches[0].clientY - touches[1].clientY

  return Math.hypot(deltaX, deltaY)
}

function getTouchCenter(touches: TouchList) {
  return {
    clientX: (touches[0].clientX + touches[1].clientX) / 2,
    clientY: (touches[0].clientY + touches[1].clientY) / 2,
  }
}

function startPinch(event: TouchEvent) {
  clearSwipeAnimationTimer()
  swipeOffsetX.value = 0
  isSwipeAnimating.value = false
  isPinching.value = true
  isDragging.value = false
  isSwiping.value = false
  hideLightboxControls()
  pinchStartDistance = getTouchDistance(event.touches)
  pinchStartZoom = zoomLevel.value
}

function onPinch(event: TouchEvent) {
  if (!isPinching.value || event.touches.length < 2 || pinchStartDistance <= 0) {
    return
  }

  const distance = getTouchDistance(event.touches)
  const center = getTouchCenter(event.touches)
  const nextZoom = pinchStartZoom * (distance / pinchStartDistance)

  zoomAtClientPoint(nextZoom, center.clientX, center.clientY)
}

function getGesturePoint(event: MouseEvent | TouchEvent) {
  if ('touches' in event) {
    const touch = event.touches[0] ?? event.changedTouches[0]

    return touch ? { clientX: touch.clientX, clientY: touch.clientY } : null
  }

  return {
    clientX: event.clientX,
    clientY: event.clientY,
  }
}

function startDrag(event: MouseEvent | TouchEvent) {
  if (!('touches' in event) && event.button !== 0) {
    return
  }

  if ('touches' in event && event.touches.length >= 2) {
    startPinch(event)
    return
  }

  const point = getGesturePoint(event)

  if (!point) {
    return
  }

  startClientX = point.clientX
  startClientY = point.clientY
  lastClientX = point.clientX
  lastClientY = point.clientY
  hasMovedInGesture = false

  if (zoomLevel.value <= 1) {
    clearSwipeAnimationTimer()
    swipeOffsetX.value = 0
    isSwipeAnimating.value = false
    isSwiping.value = true
    return
  }

  const stage = lightboxStage.value

  if (!stage) {
    return
  }

  isDragging.value = true
  hideLightboxControls()

  startScrollLeft = stage.scrollLeft
  startScrollTop = stage.scrollTop
}

function onDrag(event: MouseEvent | TouchEvent) {
  if ('touches' in event && event.touches.length >= 2) {
    onPinch(event)
    return
  }

  const point = getGesturePoint(event)

  if (!point) {
    return
  }

  const clientX = point.clientX
  const clientY = point.clientY

  const deltaX = clientX - startClientX
  const deltaY = clientY - startClientY

  lastClientX = clientX
  lastClientY = clientY
  hasMovedInGesture = hasMovedInGesture || Math.hypot(deltaX, deltaY) > 6

  if (isSwiping.value) {
    swipeOffsetX.value = currentLightboxPhotos.value.length > 1 ? resistedSwipeOffset(deltaX) : 0
    return
  }

  if (!isDragging.value) return

  const stage = lightboxStage.value

  if (!stage) {
    return
  }

  stage.scrollLeft = startScrollLeft - deltaX
  stage.scrollTop = startScrollTop - deltaY
}

function stopDrag(event?: MouseEvent | TouchEvent) {
  const point = event ? getGesturePoint(event) : null

  if (point) {
    lastClientX = point.clientX
    lastClientY = point.clientY
  }

  if (isSwiping.value) {
    const deltaX = lastClientX - startClientX
    const deltaY = lastClientY - startClientY
    const isHorizontalSwipe =
      currentLightboxPhotos.value.length > 1 &&
      Math.abs(deltaX) >= swipeThreshold &&
      Math.abs(deltaX) > Math.abs(deltaY)

    isSwiping.value = false

    if (isHorizontalSwipe) {
      const shouldShowPrevious = deltaX > 0
      settleSwipeOffset(shouldShowPrevious ? window.innerWidth : -window.innerWidth, () => {
        if (shouldShowPrevious) {
          showPreviousPhoto()
        } else {
          showNextPhoto()
        }
      })
      suppressNextClick = true
    } else if (hasMovedInGesture) {
      settleSwipeOffset(0)
      suppressNextClick = true
    } else {
      swipeOffsetX.value = 0
    }
  }

  isDragging.value = false
  isPinching.value = false
  pinchStartDistance = 0
}

function startTagDrag(event: PointerEvent, tag: ResolvedPhotoTag) {
  if (!tagEditingEnabled.value || !activePhoto.value) {
    return
  }

  event.preventDefault()
  event.stopPropagation()
  clearPhotoClickTimer()
  suppressNextClick = true
  draggedPhotoTag.value = {
    photoId: activePhoto.value.id,
    tagIndex: tag.index,
    pointerId: event.pointerId,
  }
  updateDraggedTag(event.clientX, event.clientY)
  window.addEventListener('pointermove', handleTagDragMove)
  window.addEventListener('pointerup', stopTagDrag)
  window.addEventListener('pointercancel', stopTagDrag)
}

function updateDraggedTag(clientX: number, clientY: number) {
  const draggedTag = draggedPhotoTag.value

  if (!draggedTag) {
    return
  }

  const coordinates = tagCoordinatesFromClientPoint(clientX, clientY)
  const tags = editableTagsByPhotoId.get(draggedTag.photoId)
  const tag = tags?.[draggedTag.tagIndex]

  if (!coordinates || !tag) {
    return
  }

  tag.x = coordinates.x
  tag.y = coordinates.y
  tagEditVersion.value += 1
}

function handleTagDragMove(event: PointerEvent) {
  if (draggedPhotoTag.value?.pointerId !== event.pointerId) {
    return
  }

  event.preventDefault()
  updateDraggedTag(event.clientX, event.clientY)
}

function stopTagDrag(event?: PointerEvent) {
  if (event && draggedPhotoTag.value?.pointerId !== event.pointerId) {
    return
  }

  draggedPhotoTag.value = null
  suppressNextClick = true
  window.removeEventListener('pointermove', handleTagDragMove)
  window.removeEventListener('pointerup', stopTagDrag)
  window.removeEventListener('pointercancel', stopTagDrag)
}

function photoTagGroupData(photoId: number): PhotoTagGroup {
  const tags = editableTagsByPhotoId.get(photoId) ?? []

  return {
    photo: photoId,
    tags: tags.map((tag) => {
      const serialisedTag: PhotoTag = {
        friend: tag.friend,
        x: Number(clampPercent(tag.x).toFixed(1)),
        y: Number(clampPercent(tag.y).toFixed(1)),
      }

      if (tag.position) {
        serialisedTag.position = tag.position
      }

      return serialisedTag
    }),
  }
}

function allPhotoTagGroupsData() {
  return Array.from(editableTagsByPhotoId.keys())
    .sort((a, b) => a - b)
    .map((photoId) => photoTagGroupData(photoId))
}

function serialisePhotoTagGroup(photoId: number) {
  return JSON.stringify(photoTagGroupData(photoId), null, 2)
}

function printCurrentPhotoTags() {
  if (!activePhoto.value) {
    const message = 'Open a photo in the lightbox before running tagsEdit.print().'
    console.warn(message)
    return ''
  }

  const payload = serialisePhotoTagGroup(activePhoto.value.id)
  console.log(payload)
  return payload
}

async function saveEditedPhotoTags() {
  const payload = allPhotoTagGroupsData()
  const response = await fetch('/__tags/save', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || 'Failed to save tags.')
  }

  const serialisedPayload = JSON.stringify(payload, null, 2)
  console.info('Saved current tag positions to src/data/tags.json.')
  console.log(serialisedPayload)
  return serialisedPayload
}

function enableTagEditing() {
  tagEditingEnabled.value = true
  lightboxControlsVisible.value = true
  console.info('Tag editing enabled. Run \"await tagsEdit.save()\" to save.')
}

function disableTagEditing() {
  tagEditingEnabled.value = false
  stopTagDrag()
  console.info('Tag editing disabled.')
}

function loadLightboxTagsPreference() {
  const savedValue = window.localStorage.getItem(lightboxTagsVisibleStorageKey)

  if (savedValue === 'true' || savedValue === 'false') {
    lightboxTagsVisible.value = savedValue === 'true'
  }
}

function hasCompletedTagsToggleTutorial() {
  return window.localStorage.getItem(tagsToggleTutorialStorageKey) === 'true'
}

function completeTagsToggleTutorial() {
  lightboxTagsToggleTutorialVisible.value = false
  window.localStorage.setItem(tagsToggleTutorialStorageKey, 'true')
  tagsToggleTutorialTimer = undefined
}

function startTagsToggleTutorial() {
  if (hasCompletedTagsToggleTutorial() || lightboxTagsToggleTutorialVisible.value) {
    return
  }

  lightboxTagsToggleTutorialVisible.value = true
  tagsToggleTutorialTimer = window.setTimeout(completeTagsToggleTutorial, 3_000)
}

function toggleLightboxTags() {
  lightboxTagsVisible.value = !lightboxTagsVisible.value
}

function installGalleryTagConsoleApi() {
  window.tagsEdit = {
    on: enableTagEditing,
    off: disableTagEditing,
    print: printCurrentPhotoTags,
    save: saveEditedPhotoTags,
  }
}

function uninstallGalleryTagConsoleApi() {
  if (window.tagsEdit?.on === enableTagEditing) {
    delete window.tagsEdit
  }
}

function handleLightboxPhotoClick(event: MouseEvent) {
  if (suppressNextClick) {
    suppressNextClick = false
    return
  }

  if (tagEditingEnabled.value) {
    lightboxControlsVisible.value = true
    return
  }

  clearPhotoClickTimer()
  clickToggleTimer = window.setTimeout(() => {
    lightboxControlsVisible.value = !lightboxControlsVisible.value
    clickToggleTimer = undefined
  }, 180)
}

function handleLightboxPhotoDoubleClick(event: MouseEvent) {
  clearPhotoClickTimer()
  suppressNextClick = false

  const nextZoom = zoomLevel.value > minZoom ? minZoom : doubleClickZoom
  zoomAtClientPoint(nextZoom, event.clientX, event.clientY)
}

function preloadAdjacentLightboxPhotos() {
  if (activeIndex.value === null || !currentLightboxPhotos.value.length) {
    return
  }

  const photoCount = currentLightboxPhotos.value.length
  const indexes = new Set([
    (activeIndex.value - 1 + photoCount) % photoCount,
    activeIndex.value,
    (activeIndex.value + 1) % photoCount,
  ])

  indexes.forEach((index) => {
    const photo = currentLightboxPhotos.value[index]

    if (!photo) {
      return
    }

    const image = new Image()
    image.src = photoPath(photo.filename)
  })
}

// --- Lightbox Handlers ---
function openPhoto(photoId: number, sourcePhotos = lightboxPhotos.value) {
  const index = sourcePhotos.findIndex((photo) => photo.id === photoId)

  if (index >= 0) {
    activePhotoList.value = sourcePhotos
    activeIndex.value = index
    resetLightboxViewState()
  }
}

function closeLightbox() {
  activeIndex.value = null
  activePhotoList.value = null
  resetLightboxViewState()
}

function scrollToGalleryTarget(selector: string) {
  nextTick(() => {
    window.requestAnimationFrame(() => {
      document.querySelector<HTMLElement>(selector)?.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
        inline: 'nearest',
      })
    })
  })
}

function handleHashTarget() {
  const hashTarget = decodeURIComponent(window.location.hash.slice(1)).trim()

  highlightedPhotoId.value = null
  highlightedSpecialEventId.value = null

  if (!hashTarget) {
    return
  }

  activeFilter.value = null
  closeLightbox()
  closeQrContact()

  if (/^\d+$/.test(hashTarget)) {
    const photoId = Number(hashTarget)

    if (!photosById.has(photoId)) {
      return
    }

    highlightedPhotoId.value = photoId
    scrollToGalleryTarget(`[data-gallery-photo-id="${photoId}"]`)
    return
  }

  if (!specialEvents.some((event) => event.id === hashTarget)) {
    return
  }

  highlightedSpecialEventId.value = hashTarget
  scrollToGalleryTarget(`#${CSS.escape(hashTarget)}`)
}

function showPreviousPhoto() {
  if (activeIndex.value === null || !currentLightboxPhotos.value.length) {
    return
  }

  activeIndex.value =
    (activeIndex.value - 1 + currentLightboxPhotos.value.length) % currentLightboxPhotos.value.length
  resetLightboxViewState()
}

function showNextPhoto() {
  if (activeIndex.value === null || !currentLightboxPhotos.value.length) {
    return
  }

  activeIndex.value = (activeIndex.value + 1) % currentLightboxPhotos.value.length
  resetLightboxViewState()
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

watch([activePhoto, activeQrContact], ([photo, qrContact], [previousPhoto]) => {
  document.body.classList.toggle('lightbox-open', Boolean(photo) || Boolean(qrContact))

  if (photo?.id !== previousPhoto?.id) {
    activeImageNaturalSize.value = null
  }

  if (photo) {
    if (!previousPhoto) {
      startTagsToggleTutorial()
    }

    nextTick(() => {
      updateZoomSurfaceSize()
      centreZoomStage()
    })
    preloadAdjacentLightboxPhotos()
  }
})

watch(lightboxZoomSurface, (surface, previousSurface) => {
  if (previousSurface) {
    lightboxZoomSurfaceObserver?.unobserve(previousSurface)
  }

  if (!surface) {
    updateZoomSurfaceSize()
    return
  }

  updateZoomSurfaceSize()
  lightboxZoomSurfaceObserver?.observe(surface)
})

watch(
  currentLanguage,
  (language) => {
    document.documentElement.lang = language === 'zh' ? 'zh-CN' : 'en-GB'
    window.localStorage.setItem('gallery-language', language)
  },
  { immediate: true },
)

watch(lightboxTagsVisible, (isVisible) => {
  window.localStorage.setItem(lightboxTagsVisibleStorageKey, String(isVisible))
})

onMounted(() => {
  loadLightboxTagsPreference()
  updateGalleryColumnCount()
  handleHashTarget()
  installGalleryTagConsoleApi()
  lightboxZoomSurfaceObserver = new ResizeObserver(updateZoomSurfaceSize)

  if (lightboxZoomSurface.value) {
    lightboxZoomSurfaceObserver.observe(lightboxZoomSurface.value)
  }

  clockTimer = window.setInterval(() => {
    now.value = Date.now()
  }, 60_000)

  window.addEventListener('resize', updateGalleryColumnCount)
  window.addEventListener('keydown', handleKeydown)
  window.addEventListener('hashchange', handleHashTarget)
})

onBeforeUnmount(() => {
  if (clockTimer) {
    window.clearInterval(clockTimer)
  }

  clearPhotoClickTimer()
  clearSwipeAnimationTimer()
  if (tagsToggleTutorialTimer) {
    window.clearTimeout(tagsToggleTutorialTimer)
  }
  stopTagDrag()
  uninstallGalleryTagConsoleApi()
  lightboxZoomSurfaceObserver?.disconnect()
  window.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('resize', updateGalleryColumnCount)
  window.removeEventListener('hashchange', handleHashTarget)
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
              <button
                v-else-if="part.type === 'world'"
                type="button"
                class="world-link"
                @click="applyWorldFilter(part.id)"
              >
                <span>{{ part.name }}</span>
              </button>
              <br v-else-if="part.type === 'break'" />
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
              <span class="linked-caption">
                <span class="linked-date">{{ formatLinkedDate(linkedPhoto, randomOuting.photo) }}</span>
                <span class="linked-number">#{{ linkedPhoto.id }}</span>
                <span
                  v-if="hasWorld(linkedPhoto) && linkedPhoto.world !== randomOuting.photo.world"
                  class="linked-world"
                >
                  <svg aria-hidden="true" class="world-pin" :viewBox="icons.pin.viewBox">
                    <path v-for="path in icons.pin.paths" :key="path" :d="path" />
                  </svg>
                  <span>{{ worldName(linkedPhoto.world) }}</span>
                </span>
              </span>
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

    <template v-for="(item, itemIndex) in gallerySections" :key="item.id">
      <section v-if="item.type === 'gallery' && item.rowCount" class="gallery" aria-label="VRChat photos">
        <div v-for="(column, columnIndex) in item.columns" :key="columnIndex" class="gallery-column">
          <article
            v-for="entry in column"
            :key="entry.row.photo.id"
            class="photo-card"
            :class="{ 'is-hash-target': highlightedPhotoId === entry.row.photo.id }"
            :data-gallery-photo-id="entry.row.photo.id"
          >
            <button
              class="photo-trigger"
              type="button"
              :aria-label="`${copy.open} ${entry.row.photo.filename}`"
              @click="openPhoto(entry.row.photo.id)"
            >
              <LazyPhoto
                :src="thumbnailPath(entry.row.photo.filename)"
                :alt="photoAlt(entry.row.photo)"
                :eager="itemIndex === 0 && entry.index === 0"
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
                  <button
                    v-else-if="part.type === 'world'"
                    type="button"
                    class="world-link"
                    @click="applyWorldFilter(part.id)"
                  >
                    <span>{{ part.name }}</span>
                  </button>
                  <br v-else-if="part.type === 'break'" />
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
                  :class="{ 'is-hash-target': highlightedPhotoId === linkedPhoto.id }"
                  :data-gallery-photo-id="linkedPhoto.id"
                  type="button"
                  :aria-label="`${copy.open} ${linkedPhoto.filename}`"
                  @click="openPhoto(linkedPhoto.id)"
                >
                  <LazyPhoto :src="thumbnailPath(linkedPhoto.filename)" :alt="photoAlt(linkedPhoto)" />
                  <span class="linked-caption">
                    <span class="linked-date">{{ formatLinkedDate(linkedPhoto, entry.row.photo) }}</span>
                    <span class="linked-number">#{{ linkedPhoto.id }}</span>
                    <span
                      v-if="hasWorld(linkedPhoto) && linkedPhoto.world !== entry.row.photo.world"
                      class="linked-world"
                    >
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

      <section
        v-else-if="item.type === 'special-event'"
        :id="item.event.id"
        class="special-event"
        :class="{ 'is-hash-target': highlightedSpecialEventId === item.event.id }"
        :aria-labelledby="`${item.event.id}-title`"
      >
        <div class="special-event__header">
          <p>{{ copy.specialEvent }}</p>
          <h2 :id="`${item.event.id}-title`">{{ localisedText(item.event.title_en, item.event.title_zh) }}</h2>
          <div class="special-event__meta">
            <span>{{ localisedText(item.event.date_en, item.event.date_zh) }}</span>
            <button
              v-if="hasEventWorld(item.event)"
              class="world-link"
              type="button"
              @click="applyWorldFilter(item.event.world ?? '')"
            >
              <svg aria-hidden="true" class="world-pin" :viewBox="icons.pin.viewBox">
                <path v-for="path in icons.pin.paths" :key="path" :d="path" />
              </svg>
              <span>{{ worldName(item.event.world ?? '') }}</span>
            </button>
          </div>
        </div>

        <p class="special-event__description">
          {{ localisedText(item.event.description_en, item.event.description_zh) }}
        </p>

        <div v-if="eventFriendList(item.event).length" class="friend-row special-event__friend-row">
          <span>{{ copy.with }}</span>
          <button
            v-for="friend in eventFriendList(item.event)"
            :key="friend.id"
            type="button"
            @click="applyFriendFilter(friend.id)"
          >
            {{ friend.name }}
          </button>
        </div>

        <div class="special-event__feature-grid">
          <button
            v-for="(photo, photoIndex) in item.event.featuredPhotos"
            :key="photo.id"
            class="special-event__feature"
            :class="{ 'is-hash-target': highlightedPhotoId === photo.id }"
            :data-gallery-photo-id="photo.id"
            type="button"
            :aria-label="`${copy.open} ${photo.filename}`"
            @click="openPhoto(photo.id)"
          >
            <LazyPhoto
              :src="thumbnailPath(photo.filename)"
              :alt="photoAlt(photo)"
              :eager="itemIndex === 0 && photoIndex === 0"
            />
            <span class="special-event__caption">
              <span>#{{ photo.id }}</span>
              <time :datetime="photo.captured">{{ formatSpecialEventPhotoDate(photo, item.event) }}</time>
              <span v-if="shouldShowEventPhotoWorld(photo, item.event)" class="linked-world">
                <svg aria-hidden="true" class="world-pin" :viewBox="icons.pin.viewBox">
                  <path v-for="path in icons.pin.paths" :key="path" :d="path" />
                </svg>
                <span>{{ worldName(photo.world) }}</span>
              </span>
            </span>
          </button>
        </div>

        <div v-if="item.event.linkedPhotos.length" class="special-event__linked-grid">
          <button
            v-for="photo in item.event.linkedPhotos"
            :key="photo.id"
            class="linked-trigger special-event__linked-trigger"
            :class="{ 'is-hash-target': highlightedPhotoId === photo.id }"
            :data-gallery-photo-id="photo.id"
            type="button"
            :aria-label="`${copy.open} ${photo.filename}`"
            @click="openPhoto(photo.id)"
          >
            <LazyPhoto :src="thumbnailPath(photo.filename)" :alt="photoAlt(photo)" />
            <span class="linked-caption">
              <span class="linked-date">{{ formatSpecialEventPhotoDate(photo, item.event) }}</span>
              <span class="linked-number">#{{ photo.id }}</span>
              <span v-if="shouldShowEventPhotoWorld(photo, item.event)" class="linked-world">
                <svg aria-hidden="true" class="world-pin" :viewBox="icons.pin.viewBox">
                  <path v-for="path in icons.pin.paths" :key="path" :d="path" />
                </svg>
                <span>{{ worldName(photo.world) }}</span>
              </span>
            </span>
          </button>
        </div>
      </section>
    </template>
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
      <figure class="lightbox-panel" :class="{ 'is-chrome-hidden': !lightboxControlsVisible }">
        <button class="lightbox-button lightbox-close" type="button" :aria-label="copy.close" @click="closeLightbox">
          x
        </button>
        <button v-if="currentLightboxPhotos.length > 1" class="lightbox-button lightbox-prev" type="button" :aria-label="copy.previous" @click="showPreviousPhoto">
          &lt;
        </button>
        <button v-if="currentLightboxPhotos.length > 1" class="lightbox-button lightbox-next" type="button" :aria-label="copy.next" @click="showNextPhoto">
          &gt;
        </button>

        <div class="lightbox-toolbar">
          <div v-if="lightboxTagsToggleTutorialVisible" class="lightbox-tags-hint" aria-live="polite">
            {{ copy.toggleTagsHint }}
          </div>
          <button
            class="lightbox-tags-toggle"
            :class="{ 'is-active': lightboxTagsVisible, 'is-tutorial': lightboxTagsToggleTutorialVisible }"
            type="button"
            :aria-pressed="lightboxTagsVisible"
            :aria-label="copy.showTagsLabel"
            @click.stop="toggleLightboxTags"
          >
            {{ copy.showTags }}
          </button>
          <div class="lightbox-title">
            <span>{{ activePosition }} / {{ currentLightboxPhotos.length }}</span>
          </div>
        </div>

        <div ref="lightboxStage" class="lightbox-stage">
          <div
            ref="lightboxZoomSurface"
            class="lightbox-zoom-surface"
            :style="zoomSurfaceStyle"
            @wheel.prevent="handleScrollZoom"
            @mousedown="startDrag"
            @mousemove="onDrag"
            @mouseup="stopDrag"
            @mouseleave="stopDrag"
            @touchstart="startDrag"
            @touchmove.prevent="onDrag"
            @touchend="stopDrag"
            @touchcancel="stopDrag"
            @click="handleLightboxPhotoClick"
            @dblclick.prevent="handleLightboxPhotoDoubleClick"
          >
            <div
              class="lightbox-image-frame"
              :class="{ 'is-swipe-animating': isSwipeAnimating }"
              :style="lightboxImageFrameStyle"
            >
              <img
                class="lightbox-image"
                :src="photoPath(activePhoto.filename)"
                :alt="photoAlt(activePhoto)"
                :style="lightboxImageStyle"
                @load="handleLightboxImageLoad"
                @dragstart.prevent
              />
              <div
                v-if="activeImageNaturalSize && activePhotoTags.length && lightboxTagsVisible"
                class="lightbox-tags"
                :class="{ 'is-editing': tagEditingEnabled }"
                :aria-label="copy.taggedFriends"
              >
                <button
                  v-for="tag in activePhotoTags"
                  :key="`${tag.friendId}-${tag.index}`"
                  class="lightbox-tag"
                  :class="photoTagClass(tag)"
                  :style="photoTagStyle(tag)"
                  type="button"
                  :aria-label="tag.name"
                  @pointerdown="startTagDrag($event, tag)"
                  @click.stop="tagEditingEnabled || applyFriendFilter(tag.friendId, true)"
                >
                  <span class="lightbox-tag__dot" aria-hidden="true"></span>
                  <span class="lightbox-tag__label">{{ tag.name }}</span>
                </button>
              </div>
            </div>
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
              <button
                v-else-if="part.type === 'world'"
                type="button"
                class="world-link"
                @click="applyWorldFilter(part.id, true)"
              >
                <span>{{ part.name }}</span>
              </button>
              <br v-else-if="part.type === 'break'" />
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
