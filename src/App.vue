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
    editmode?: {
      on: () => void
      off: () => void
      toggle: () => boolean
      status: () => boolean
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
  | { type: 'text'; text: string; emphasis?: boolean }
  | { type: 'break'; emphasis?: boolean }
  | { type: 'friend'; id: string; name: string; emphasis?: boolean }
  | { type: 'world'; id: string; name: string; emphasis?: boolean }
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
type TagPosition = NonNullable<PhotoTag['position']>
type PendingEntityKind = 'world' | 'friend' | 'tag'

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
  { label: 'maao.cc', icon: 'home', href: 'https://maao.cc/' },
  { label: 'GitHub', icon: 'github', href: 'https://github.com/maoawa/mars-vrchat-gallery' },
  { label: 'X', icon: 'x', href: 'https://twitter.com/winmemzqwq' },
  { label: 'Telegram', icon: 'telegram', href: 'https://t.me/maoawa' },
  { label: 'Discord', icon: 'discord', href: 'https://discord.com/users/742704239410675725' },
  { label: 'Facebook', icon: 'facebook', href: 'https://www.facebook.com/profile.php?id=100088742570811' },
  { label: 'Instagram', icon: 'instagram', href: 'https://www.instagram.com/winmemzqwq' },
]
const emailContact = { label: 'Email', icon: 'email' as Icon }
const emailNameParts = ['winmemz', 'qwq']
const emailDomainParts = ['gmail', 'com']
const emailSchemeParts = ['ma', 'il', 'to']
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
const introExpanded = ref(false)
const introDismissed = ref(false)
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
const introDismissedStorageKey = 'gallery-intro-dismissed'
const editModeStorageKey = 'gallery-edit-mode-enabled'
const editPanelCollapsedStorageKey = 'gallery-edit-panel-collapsed'
const isDevelopment = import.meta.env.DEV

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
const editModeEnabled = ref(false)
const editPanelCollapsed = ref(false)
const tagEditVersion = ref(0)
const metadataEditVersion = ref(0)
const draggedPhotoTag = ref<DraggedPhotoTag | null>(null)
const worldEditQuery = ref('')
const friendEditQuery = ref('')
const tagFriendEditQuery = ref('')
const parentPhotoEditQuery = ref('')
const linkedPhotoEditQuery = ref('')
const editSaveState = ref<'idle' | 'dirty' | 'saving' | 'saved' | 'error'>('idle')
const editSaveMessage = ref('')
const pendingEntityKind = ref<PendingEntityKind | null>(null)
const newEntityId = ref('')
const newEntityNameEn = ref('')
const newEntityNameZh = ref('')
const newEntityLink = ref('')
const newEntityError = ref('')

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
const buildTimeIso = __BUILD_TIME__
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
  metadataEditVersion.value

  if (activeIndex.value === null) {
    return null
  }

  return currentLightboxPhotos.value[activeIndex.value] ?? null
})

function normaliseSearch(value: string) {
  return value.trim().toLocaleLowerCase()
}

function entityMatchesQuery(entity: Friend | World, query: string) {
  const search = normaliseSearch(query)

  if (!search) {
    return true
  }

  return [entity.id, entity.name_en, entity.name_zh ?? ''].some((value) =>
    normaliseSearch(value).includes(search),
  )
}

function exactEntityMatch<T extends Friend | World>(entities: T[], query: string) {
  const search = normaliseSearch(query)
  return entities.find((entity) =>
    [entity.id, entity.name_en, entity.name_zh ?? ''].some((value) => normaliseSearch(value) === search),
  )
}

function uniqueEntityId(name: string, separator: '.' | '_', existingIds: Set<string>, prefix: string) {
  const base = name
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase()
    .replace(/[^a-z0-9]+/g, separator)
    .replace(new RegExp(`\\${separator}+`, 'g'), separator)
    .replace(new RegExp(`^\\${separator}|\\${separator}$`, 'g'), '') || prefix
  let id = base
  let suffix = 2

  while (existingIds.has(id)) {
    id = `${base}${separator}${suffix}`
    suffix += 1
  }

  return id
}

const worldEditSuggestions = computed(() => {
  metadataEditVersion.value
  return worlds.filter((world) => entityMatchesQuery(world, worldEditQuery.value)).slice(0, 7)
})
const friendEditSuggestions = computed(() => {
  metadataEditVersion.value
  const selected = new Set(activePhoto.value?.friend ?? [])
  return friends
    .filter((friend) => !selected.has(friend.id) && entityMatchesQuery(friend, friendEditQuery.value))
    .slice(0, 7)
})
const tagFriendEditSuggestions = computed(() => {
  tagEditVersion.value
  metadataEditVersion.value
  const selected = new Set((activePhoto.value ? editableTagsByPhotoId.get(activePhoto.value.id) : [])?.map((tag) => tag.friend))
  return friends
    .filter((friend) => !selected.has(friend.id) && entityMatchesQuery(friend, tagFriendEditQuery.value))
    .slice(0, 7)
})

function photoMatchesEditQuery(photo: GalleryImage, query: string) {
  const search = normaliseSearch(query).replace(/^#/, '')

  if (!search) {
    return true
  }

  return String(photo.id).includes(search)
}

function wouldCreatePhotoCycle(photo: GalleryImage, parent: GalleryImage) {
  const visited = new Set<number>()
  let cursor: GalleryImage | undefined = parent

  while (cursor && !visited.has(cursor.id)) {
    if (cursor.id === photo.id) return true
    visited.add(cursor.id)
    cursor = cursor.parent ? photosById.get(cursor.parent) : undefined
  }

  return false
}

const availableRelationPhotos = computed(() => {
  metadataEditVersion.value
  const activeId = activePhoto.value?.id
  return photos.filter((photo) => photo.id !== activeId)
})
const parentPhotoEditSuggestions = computed(() => {
  const currentPhoto = activePhoto.value
  return availableRelationPhotos.value
    .filter(
      (photo) =>
        (!currentPhoto || !wouldCreatePhotoCycle(currentPhoto, photo)) &&
        photoMatchesEditQuery(photo, parentPhotoEditQuery.value),
    )
    .slice(0, 7)
})
const linkedPhotoEditSuggestions = computed(() => {
  const linkedIds = new Set(activePhoto.value?.linked ?? [])
  const currentPhoto = activePhoto.value
  return availableRelationPhotos.value
    .filter(
      (photo) =>
        !linkedIds.has(photo.id) &&
        (!currentPhoto || !wouldCreatePhotoCycle(photo, currentPhoto)) &&
        photoMatchesEditQuery(photo, linkedPhotoEditQuery.value),
    )
    .slice(0, 7)
})
const activeParentPhoto = computed(() => {
  metadataEditVersion.value
  return activePhoto.value?.parent ? photosById.get(activePhoto.value.parent) ?? null : null
})
const activeLinkedPhotos = computed(() => {
  metadataEditVersion.value
  return (activePhoto.value?.linked ?? [])
    .map((photoId) => photosById.get(photoId))
    .filter((photo): photo is GalleryImage => Boolean(photo))
})

function markEditDirty() {
  editSaveState.value = 'dirty'
  editSaveMessage.value = 'Unsaved changes'
}

function touchMetadata() {
  metadataEditVersion.value += 1
  markEditDirty()
}

function beginEntityCreation(kind: PendingEntityKind, query: string) {
  const isWorld = kind === 'world'
  const entities = isWorld ? worlds : friends
  pendingEntityKind.value = kind
  newEntityId.value = uniqueEntityId(
    query,
    isWorld ? '.' : '_',
    new Set(entities.map((entity) => entity.id)),
    isWorld ? 'world' : 'friend',
  )
  newEntityNameEn.value = query.trim()
  newEntityNameZh.value = ''
  newEntityLink.value = ''
  newEntityError.value = ''
}

function cancelEntityCreation() {
  pendingEntityKind.value = null
  newEntityId.value = ''
  newEntityNameEn.value = ''
  newEntityNameZh.value = ''
  newEntityLink.value = ''
  newEntityError.value = ''
}

function submitNewEntity() {
  const kind = pendingEntityKind.value
  const id = newEntityId.value.trim()
  const nameEn = newEntityNameEn.value.trim()

  if (!kind || !id || !nameEn) {
    newEntityError.value = 'ID and name_en are required.'
    return
  }

  const isWorld = kind === 'world'
  const entities = isWorld ? worlds : friends
  if (entities.some((entity) => entity.id === id)) {
    newEntityError.value = `The ID “${id}” already exists.`
    return
  }

  const entity = {
    id,
    name_en: nameEn,
    ...(newEntityNameZh.value.trim() ? { name_zh: newEntityNameZh.value.trim() } : {}),
  }

  if (isWorld) {
    const world: World = {
      ...entity,
      ...(newEntityLink.value.trim() ? { link: newEntityLink.value.trim() } : {}),
    }
    worlds.push(world)
    worldsById.set(world.id, world)
    cancelEntityCreation()
    selectWorld(world)
    return
  }

  const friend = entity as Friend
  friends.push(friend)
  friendsById.set(friend.id, friend)
  cancelEntityCreation()
  if (kind === 'tag') addPhotoTag(friend)
  else addPhotoFriend(friend)
}

function selectWorld(world: World) {
  if (!activePhoto.value) return
  activePhoto.value.world = world.id
  worldEditQuery.value = ''
  touchMetadata()
}

function commitWorld() {
  const query = worldEditQuery.value.trim()
  if (!query) return
  const existingWorld = exactEntityMatch(worlds, query)
  if (existingWorld) selectWorld(existingWorld)
  else beginEntityCreation('world', query)
}

function autocompleteWorld(event: KeyboardEvent) {
  const suggestion = worldEditSuggestions.value[0]
  if (!suggestion) return
  event.preventDefault()
  worldEditQuery.value = suggestion.id
}

function clearWorld() {
  if (!activePhoto.value) return
  activePhoto.value.world = ''
  touchMetadata()
}

function addPhotoFriend(friend: Friend) {
  if (!activePhoto.value || activePhoto.value.friend.includes(friend.id)) return
  activePhoto.value.friend = [
    ...new Set([...activePhoto.value.friend.filter((friendId) => friendId.trim()), friend.id]),
  ]
  friendEditQuery.value = ''
  touchMetadata()
}

function commitPhotoFriend() {
  const query = friendEditQuery.value.trim()
  if (!query) return
  const existingFriend = exactEntityMatch(friends, query)
  if (existingFriend) addPhotoFriend(existingFriend)
  else beginEntityCreation('friend', query)
}

function autocompletePhotoFriend(event: KeyboardEvent) {
  const suggestion = friendEditSuggestions.value[0]
  if (!suggestion) return
  event.preventDefault()
  friendEditQuery.value = suggestion.id
}

function removePhotoFriend(friendId: string) {
  if (!activePhoto.value) return
  activePhoto.value.friend = activePhoto.value.friend.filter((id) => id !== friendId)
  const tags = editableTagsByPhotoId.get(activePhoto.value.id)
  if (tags) {
    editableTagsByPhotoId.set(activePhoto.value.id, tags.filter((tag) => tag.friend !== friendId))
    tagEditVersion.value += 1
  }
  touchMetadata()
}

function setPhotoParent(photo: GalleryImage, parent: GalleryImage | null) {
  if (parent && wouldCreatePhotoCycle(photo, parent)) return
  const previousParent = photo.parent ? photosById.get(photo.parent) : null
  if (previousParent) {
    previousParent.linked = (previousParent.linked ?? []).filter((photoId) => photoId !== photo.id)
    if (!previousParent.linked.length) delete previousParent.linked
  }

  if (!parent) {
    delete photo.parent
    touchMetadata()
    return
  }

  photo.parent = parent.id
  parent.linked = [...new Set([...(parent.linked ?? []), photo.id])]
  touchMetadata()
}

function selectParentPhoto(photo: GalleryImage) {
  if (!activePhoto.value) return
  setPhotoParent(activePhoto.value, photo)
  parentPhotoEditQuery.value = ''
}

function commitParentPhoto() {
  const suggestion = parentPhotoEditSuggestions.value[0]
  if (suggestion) selectParentPhoto(suggestion)
}

function autocompleteParentPhoto(event: KeyboardEvent) {
  const suggestion = parentPhotoEditSuggestions.value[0]
  if (!suggestion) return
  event.preventDefault()
  parentPhotoEditQuery.value = `#${suggestion.id}`
}

function addLinkedPhoto(photo: GalleryImage) {
  if (!activePhoto.value) return
  setPhotoParent(photo, activePhoto.value)
  linkedPhotoEditQuery.value = ''
}

function commitLinkedPhoto() {
  const suggestion = linkedPhotoEditSuggestions.value[0]
  if (suggestion) addLinkedPhoto(suggestion)
}

function autocompleteLinkedPhoto(event: KeyboardEvent) {
  const suggestion = linkedPhotoEditSuggestions.value[0]
  if (!suggestion) return
  event.preventDefault()
  linkedPhotoEditQuery.value = `#${suggestion.id}`
}

function removeLinkedPhoto(photo: GalleryImage) {
  if (!activePhoto.value) return
  const parent = activePhoto.value
  parent.linked = (parent.linked ?? []).filter((photoId) => photoId !== photo.id)
  if (!parent.linked.length) delete parent.linked
  if (photo.parent === parent.id) delete photo.parent
  touchMetadata()
}

function addPhotoTag(friend: Friend) {
  if (!activePhoto.value) return
  const tags = editableTagsByPhotoId.get(activePhoto.value.id) ?? []
  if (tags.some((tag) => tag.friend === friend.id)) return
  tags.push({ friend: friend.id, x: 50, y: 50, position: 'bottom' })
  editableTagsByPhotoId.set(activePhoto.value.id, tags)
  if (!activePhoto.value.friend.includes(friend.id)) {
    activePhoto.value.friend = [
      ...new Set([...activePhoto.value.friend.filter((friendId) => friendId.trim()), friend.id]),
    ]
  }
  tagFriendEditQuery.value = ''
  tagEditVersion.value += 1
  touchMetadata()
}

function commitPhotoTag() {
  const query = tagFriendEditQuery.value.trim()
  if (!query) return
  const existingFriend = exactEntityMatch(friends, query)
  if (existingFriend) addPhotoTag(existingFriend)
  else beginEntityCreation('tag', query)
}

function autocompletePhotoTag(event: KeyboardEvent) {
  const suggestion = tagFriendEditSuggestions.value[0]
  if (!suggestion) return
  event.preventDefault()
  tagFriendEditQuery.value = suggestion.id
}

const tagPositionOrder: TagPosition[] = ['bottom', 'top', 'left', 'right']
const tagPositionLabels: Record<TagPosition, string> = {
  bottom: 'BOTTOM',
  top: 'UP',
  left: 'LEFT',
  right: 'RIGHT',
}

function updatePhotoDescription(field: 'description_en' | 'description_zh', event: Event) {
  if (!activePhoto.value || !(event.target instanceof HTMLTextAreaElement)) return
  activePhoto.value[field] = event.target.value
  touchMetadata()
}

function cycleTagPosition(tagIndex: number) {
  if (!activePhoto.value) return
  const tag = editableTagsByPhotoId.get(activePhoto.value.id)?.[tagIndex]
  if (!tag) return
  const currentPosition = tag.position ?? 'bottom'
  tag.position = tagPositionOrder[(tagPositionOrder.indexOf(currentPosition) + 1) % tagPositionOrder.length]
  tagEditVersion.value += 1
  markEditDirty()
}

function removePhotoTag(tagIndex: number) {
  if (!activePhoto.value) return
  editableTagsByPhotoId.get(activePhoto.value.id)?.splice(tagIndex, 1)
  tagEditVersion.value += 1
  markEditDirty()
}

function resetEditQueries() {
  worldEditQuery.value = ''
  friendEditQuery.value = ''
  tagFriendEditQuery.value = ''
  parentPhotoEditQuery.value = ''
  linkedPhotoEditQuery.value = ''
  cancelEntityCreation()
}

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
const lastUpdatedText = computed(() => {
  const buildTime = new Date(buildTimeIso)

  if (Number.isNaN(buildTime.getTime())) {
    return ''
  }

  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(buildTime)
})
const lastUpdatedTimezone = computed(() => formatUtcOffset(new Date(buildTimeIso)))

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

const activePhotoFriendIds = computed(() => {
  if (!activePhoto.value) return []
  return [...new Set(activePhoto.value.friend.map((friendId) => friendId.trim()).filter(Boolean))]
})

const canGenerateCurrentPhotoTags = computed(
  () => activePhotoTags.value.length === 0 && activePhotoFriendIds.value.length > 0,
)

function generateCurrentPhotoTags() {
  if (!activePhoto.value || !canGenerateCurrentPhotoTags.value) return
  const friendIds = activePhotoFriendIds.value
  const left = 38
  const right = 62
  const step = friendIds.length > 1 ? (right - left) / (friendIds.length - 1) : 0

  editableTagsByPhotoId.set(
    activePhoto.value.id,
    friendIds.map((friendId, index) => ({
      friend: friendId,
      x: friendIds.length === 1 ? 50 : Number((left + step * index).toFixed(1)),
      y: 50,
    })),
  )
  lightboxTagsVisible.value = true
  tagEditVersion.value += 1
  markEditDirty()
}

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

function outingFriendList(row: GalleryRow) {
  const friendIds = [row.photo, ...row.linkedPhotos].flatMap((photo) => photo.friend)

  return [...new Set(friendIds)]
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

function descriptionParts(description: string, emphasis = false, parseEmphasis = true) {
  const parts: DescriptionPart[] = []
  const friendPattern = /\[\[([a-zA-Z0-9_-]+)\]\]/g
  const worldPattern = /\{\{([a-zA-Z0-9_.-]+)\}\}/g
  const emphasisPattern = parseEmphasis ? /\*([^*\n]+)\*/g : null
  const breakPattern = /<br\s*\/?>/gi
  let cursor = 0

  while (cursor < description.length) {
    friendPattern.lastIndex = cursor
    worldPattern.lastIndex = cursor
    if (emphasisPattern) {
      emphasisPattern.lastIndex = cursor
    }
    breakPattern.lastIndex = cursor

    const friendMatch = friendPattern.exec(description)
    const worldMatch = worldPattern.exec(description)
    const emphasisMatch = emphasisPattern?.exec(description) ?? null
    const breakMatch = breakPattern.exec(description)
    const matches = [
      friendMatch ? { kind: 'friend' as const, match: friendMatch } : null,
      worldMatch ? { kind: 'world' as const, match: worldMatch } : null,
      emphasisMatch ? { kind: 'emphasis' as const, match: emphasisMatch } : null,
      breakMatch ? { kind: 'break' as const, match: breakMatch } : null,
    ].filter((item): item is NonNullable<typeof item> => Boolean(item))
    const nextMatch = matches.sort((a, b) => a.match.index - b.match.index)[0]

    if (!nextMatch) {
      parts.push({ type: 'text', text: description.slice(cursor), emphasis })
      break
    }

    if (nextMatch.match.index > cursor) {
      parts.push({ type: 'text', text: description.slice(cursor, nextMatch.match.index), emphasis })
    }

    if (nextMatch.kind === 'friend') {
      parts.push({
        type: 'friend',
        id: nextMatch.match[1],
        name: friendName(nextMatch.match[1]),
        emphasis,
      })
    } else if (nextMatch.kind === 'world') {
      const worldId = nextMatch.match[1]

      parts.push(
        worldsById.has(worldId)
          ? {
              type: 'world',
              id: worldId,
              name: worldName(worldId),
              emphasis,
            }
          : { type: 'text', text: nextMatch.match[0], emphasis },
      )
    } else if (nextMatch.kind === 'emphasis') {
      parts.push(...descriptionParts(nextMatch.match[1], true, false))
    } else {
      parts.push({ type: 'break', emphasis })
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

function dismissIntro() {
  introDismissed.value = true
  introExpanded.value = false
  window.localStorage.setItem(introDismissedStorageKey, 'true')
}

function formatUtcOffset(date: Date) {
  const offsetMinutes = -date.getTimezoneOffset()
  const sign = offsetMinutes >= 0 ? '+' : '-'
  const absoluteMinutes = Math.abs(offsetMinutes)
  const hours = Math.floor(absoluteMinutes / 60)
  const minutes = absoluteMinutes % 60

  return minutes === 0 ? `UTC${sign}${hours}` : `UTC${sign}${hours}:${String(minutes).padStart(2, '0')}`
}

function openEmail() {
  const address = `${emailNameParts.join('')}@${emailDomainParts.join('.')}`
  window.location.href = [emailSchemeParts.join(''), address].join(':')
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
  if (!editModeEnabled.value || !activePhoto.value) {
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
  markEditDirty()
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

function currentPhotoEditData() {
  if (!activePhoto.value) {
    return null
  }

  return {
    image: activePhoto.value,
    tags: photoTagGroupData(activePhoto.value.id).tags,
  }
}

function printCurrentPhotoMetadata() {
  const currentData = currentPhotoEditData()

  if (!currentData) {
    const message = 'Open a photo in the lightbox before running editmode.print().'
    console.warn(message)
    return ''
  }

  const payload = JSON.stringify(currentData, null, 2)
  console.log(payload)
  return payload
}

function allGalleryEditData() {
  return {
    images: [...photos].sort((a, b) => a.id - b.id),
    friends,
    worlds,
    tags: allPhotoTagGroupsData(),
  }
}

async function saveEditedGalleryData() {
  editSaveState.value = 'saving'
  editSaveMessage.value = 'Saving…'

  try {
    const payload = allGalleryEditData()
    const response = await fetch('/__gallery/save', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })

    if (!response.ok) {
      const message = await response.text()
      throw new Error(message || 'Failed to save gallery metadata.')
    }

    const serialisedPayload = JSON.stringify(payload, null, 2)
    editSaveState.value = 'saved'
    editSaveMessage.value = 'Saved to src/data/*.json'
    console.info('Saved gallery metadata and tag positions to src/data/*.json.')
    return serialisedPayload
  } catch (error) {
    editSaveState.value = 'error'
    editSaveMessage.value = error instanceof Error ? error.message : 'Save failed'
    throw error
  }
}

function enableEditMode() {
  editModeEnabled.value = true
  window.localStorage.setItem(editModeStorageKey, 'true')
  lightboxControlsVisible.value = true
  lightboxTagsVisible.value = true
  console.info('Edit mode enabled. Run \"await editmode.save()\" to save.')
}

function disableEditMode() {
  editModeEnabled.value = false
  window.localStorage.setItem(editModeStorageKey, 'false')
  stopTagDrag()
  console.info('Edit mode disabled.')
}

function toggleEditMode() {
  if (editModeEnabled.value) {
    disableEditMode()
  } else {
    enableEditMode()
  }

  return editModeEnabled.value
}

function toggleEditPanel() {
  editPanelCollapsed.value = !editPanelCollapsed.value
  window.localStorage.setItem(editPanelCollapsedStorageKey, String(editPanelCollapsed.value))
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

function installGalleryEditConsoleApi() {
  window.editmode = {
    on: enableEditMode,
    off: disableEditMode,
    toggle: toggleEditMode,
    status: () => editModeEnabled.value,
    print: printCurrentPhotoMetadata,
    save: saveEditedGalleryData,
  }
}

function uninstallGalleryEditConsoleApi() {
  if (window.editmode?.on === enableEditMode) {
    delete window.editmode
  }
}

function handleLightboxPhotoClick(event: MouseEvent) {
  if (suppressNextClick) {
    suppressNextClick = false
    return
  }

  if (editModeEnabled.value) {
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

  const target = event.target
  if (
    target instanceof HTMLInputElement ||
    target instanceof HTMLTextAreaElement ||
    target instanceof HTMLSelectElement ||
    (target instanceof HTMLElement && target.isContentEditable)
  ) {
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
    resetEditQueries()
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
  introDismissed.value = window.localStorage.getItem(introDismissedStorageKey) === 'true'
  editModeEnabled.value = window.localStorage.getItem(editModeStorageKey) === 'true'
  editPanelCollapsed.value = window.localStorage.getItem(editPanelCollapsedStorageKey) === 'true'
  loadLightboxTagsPreference()
  if (editModeEnabled.value) lightboxTagsVisible.value = true
  updateGalleryColumnCount()
  handleHashTarget()
  installGalleryEditConsoleApi()
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
  uninstallGalleryEditConsoleApi()
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
      <div v-if="!introDismissed" class="lede" :class="{ 'lede-cn': currentLanguage === 'zh' }">
        <p>
          <template v-if="introExpanded">
            {{ copy.introBeforeLink }}
            <a href="https://maao.cc/" target="_blank" rel="noreferrer">maao.cc</a>
            {{ copy.introAfterLink }}
          </template>
          <template v-else>
            {{ copy.introShort }}
          </template>
          <button class="lede-inline-button" type="button" :aria-expanded="introExpanded" @click="introExpanded = !introExpanded">
            {{ introExpanded ? copy.introLess : copy.introMore }}
          </button>
        </p>
        <button v-if="introExpanded" class="lede-dismiss-button" type="button" @click="dismissIntro">
          {{ copy.introDismiss }}
        </button>
      </div>

      <nav class="footer-social header-social" :aria-label="copy.socialLinksLabel">
        <a
          v-for="link in socialLinks"
          :key="link.label"
          :href="link.href"
          :aria-label="link.label"
          target="_blank"
          rel="noreferrer"
        >
          <svg
            aria-hidden="true"
            class="social-icon"
            :class="{ 'social-icon--home': link.icon === 'home' }"
            :viewBox="icons[link.icon].viewBox"
          >
            <defs v-if="link.icon === 'home'">
              <linearGradient id="personal-home-gradient" x1="88" y1="72" x2="552" y2="576" gradientUnits="userSpaceOnUse">
                <stop offset="0" stop-color="#f4d6aa" />
                <stop offset="0.36" stop-color="#9fd2bd" />
                <stop offset="0.68" stop-color="#b7c7ff" />
                <stop offset="1" stop-color="#f0b6d7" />
              </linearGradient>
            </defs>
            <path v-for="path in icons[link.icon].paths" :key="path" :d="path" />
          </svg>
        </a>

        <button type="button" :aria-label="emailContact.label" @click="openEmail">
          <svg aria-hidden="true" class="social-icon" :viewBox="icons[emailContact.icon].viewBox">
            <path v-for="path in icons[emailContact.icon].paths" :key="path" :d="path" />
          </svg>
        </button>

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
                :class="{ 'description-emphasis': part.emphasis }"
                @click="applyFriendFilter(part.id)"
              >
                {{ part.name }}
              </button>
              <button
                v-else-if="part.type === 'world'"
                type="button"
                class="world-link"
                :class="{ 'description-emphasis': part.emphasis }"
                @click="applyWorldFilter(part.id)"
              >
                <span>{{ part.name }}</span>
              </button>
              <br v-else-if="part.type === 'break'" />
              <em v-else-if="part.emphasis">{{ part.text }}</em>
              <template v-else>{{ part.text }}</template>
            </template>
          </p>

          <div v-if="outingFriendList(randomOuting).length" class="friend-row" aria-label="Friends in this outing">
            <span>{{ copy.with }}</span>
            <button
              v-for="friend in outingFriendList(randomOuting)"
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
                    :class="{ 'description-emphasis': part.emphasis }"
                    @click="applyFriendFilter(part.id)"
                  >
                    {{ part.name }}
                  </button>
                  <button
                    v-else-if="part.type === 'world'"
                    type="button"
                    class="world-link"
                    :class="{ 'description-emphasis': part.emphasis }"
                    @click="applyWorldFilter(part.id)"
                  >
                    <span>{{ part.name }}</span>
                  </button>
                  <br v-else-if="part.type === 'break'" />
                  <em v-else-if="part.emphasis">{{ part.text }}</em>
                  <template v-else>{{ part.text }}</template>
                </template>
              </p>

              <div v-if="outingFriendList(entry.row).length" class="friend-row" aria-label="Friends in this photo">
                <span>{{ copy.with }}</span>
                <button
                  v-for="friend in outingFriendList(entry.row)"
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

    <div class="footer-contact">
      <p>{{ copy.photoTimesNote }}</p>
      <p v-if="lastUpdatedText">
        {{ copy.lastUpdated }}:
        <time :datetime="buildTimeIso">{{ lastUpdatedText }} ({{ lastUpdatedTimezone }})</time>
      </p>
      <p>
        {{ copy.copyrightBeforeLink }}
        <a href="https://maao.cc/" target="_blank" rel="noreferrer">maao.cc</a>
        {{ copy.copyrightAfterLink }}
      </p>
    </div>
  </footer>

  <Teleport to="body">
    <button
      v-if="isDevelopment && !activeQrContact && (!editModeEnabled || !activePhoto)"
      class="edit-mode-dev-toggle"
      :class="{ 'is-active': editModeEnabled }"
      type="button"
      :aria-pressed="editModeEnabled"
      @click="toggleEditMode"
    >
      Edit mode: {{ editModeEnabled ? 'ON' : 'OFF' }}
    </button>

    <div v-if="activeQrContact" class="qr-modal" role="dialog" aria-modal="true" @click.self="closeQrContact">
      <section class="qr-panel" :aria-label="activeQrContact.label">
        <button class="qr-close" type="button" :aria-label="copy.close" @click="closeQrContact">
          <svg aria-hidden="true" class="close-icon" :viewBox="icons.close.viewBox">
            <path v-for="path in icons.close.paths" :key="path" :d="path" />
          </svg>
        </button>
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
          <svg aria-hidden="true" class="close-icon" :viewBox="icons.close.viewBox">
            <path v-for="path in icons.close.paths" :key="path" :d="path" />
          </svg>
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

        <aside
          v-if="editModeEnabled"
          class="edit-panel"
          :class="{ 'is-collapsed': editPanelCollapsed }"
          aria-label="Photo editor"
          @click.stop
          @dblclick.stop
          @pointerdown.stop
        >
          <header class="edit-panel__header">
            <button
              class="edit-panel__collapse"
              type="button"
              :aria-label="editPanelCollapsed ? 'Expand edit panel' : 'Collapse edit panel'"
              :aria-expanded="!editPanelCollapsed"
              @click="toggleEditPanel"
            >
              {{ editPanelCollapsed ? '+' : '−' }}
            </button>
            <div>
              <span>Edit mode</span>
              <strong>Edit photo #{{ activePhoto.id }}</strong>
            </div>
            <button class="edit-panel__mode-toggle" type="button" aria-label="Turn off edit mode" @click="disableEditMode">
              ON
            </button>
          </header>

          <template v-if="!editPanelCollapsed">
          <form v-if="pendingEntityKind" class="edit-new-entity" @submit.prevent="submitNewEntity">
            <div class="edit-new-entity__header">
              <strong>New {{ pendingEntityKind === 'world' ? 'world' : 'friend' }}</strong>
              <button type="button" @click="cancelEntityCreation">Cancel</button>
            </div>
            <label>
              <span>ID *</span>
              <input v-model="newEntityId" type="text" autocomplete="off" required />
            </label>
            <label>
              <span>name_en *</span>
              <input v-model="newEntityNameEn" type="text" autocomplete="off" required />
            </label>
            <label>
              <span>name_zh</span>
              <input v-model="newEntityNameZh" type="text" autocomplete="off" />
            </label>
            <label v-if="pendingEntityKind === 'world'">
              <span>link</span>
              <input v-model="newEntityLink" type="url" autocomplete="off" placeholder="https://…" />
            </label>
            <p v-if="newEntityError" class="edit-new-entity__error">{{ newEntityError }}</p>
            <button class="edit-new-entity__submit" type="submit">
              Create {{ pendingEntityKind === 'world' ? 'world' : 'friend' }}
            </button>
          </form>

          <section class="edit-field">
            <label for="edit-world">World</label>
            <div v-if="hasWorld(activePhoto)" class="edit-chips">
              <span class="edit-chip">
                {{ worldName(activePhoto.world) }}
                <small>{{ activePhoto.world }}</small>
                <button type="button" aria-label="Remove world" @click="clearWorld">×</button>
              </span>
            </div>
            <div v-else class="edit-autocomplete">
              <input
                id="edit-world"
                v-model="worldEditQuery"
                type="text"
                autocomplete="off"
                placeholder="Search world name or ID"
                @keydown.tab="autocompleteWorld"
                @keydown.enter.prevent="commitWorld"
              />
              <div v-if="worldEditQuery.trim()" class="edit-suggestions">
                <button
                  v-for="world in worldEditSuggestions"
                  :key="world.id"
                  type="button"
                  @mousedown.prevent="selectWorld(world)"
                >
                  <span>{{ localisedText(world.name_en, world.name_zh) }}</span>
                  <small>{{ world.id }}</small>
                </button>
                <p>Tab completes the first result · Enter selects or creates</p>
              </div>
            </div>
          </section>

          <section class="edit-field edit-field--descriptions">
            <label for="edit-description-en">DESCRIPTION (EN)</label>
            <textarea
              id="edit-description-en"
              :value="activePhoto.description_en ?? ''"
              rows="3"
              placeholder="English description"
              @input="updatePhotoDescription('description_en', $event)"
            ></textarea>
            <label for="edit-description-zh">DESCRIPTION (ZH)</label>
            <textarea
              id="edit-description-zh"
              :value="activePhoto.description_zh ?? ''"
              rows="3"
              placeholder="Chinese description"
              @input="updatePhotoDescription('description_zh', $event)"
            ></textarea>
          </section>

          <section class="edit-field">
            <label for="edit-friend">Friends</label>
            <div class="edit-chips">
              <span v-for="friend in friendList(activePhoto)" :key="friend.id" class="edit-chip">
                {{ friend.name }}
                <small>{{ friend.id }}</small>
                <button type="button" :aria-label="`Remove ${friend.name}`" @click="removePhotoFriend(friend.id)">×</button>
              </span>
            </div>
            <div class="edit-autocomplete">
              <input
                id="edit-friend"
                v-model="friendEditQuery"
                type="text"
                autocomplete="off"
                placeholder="Search friend name or ID"
                @keydown.tab="autocompletePhotoFriend"
                @keydown.enter.prevent="commitPhotoFriend"
              />
              <div v-if="friendEditQuery.trim()" class="edit-suggestions">
                <button
                  v-for="friend in friendEditSuggestions"
                  :key="friend.id"
                  type="button"
                  @mousedown.prevent="addPhotoFriend(friend)"
                >
                  <span>{{ localisedText(friend.name_en, friend.name_zh) }}</span>
                  <small>{{ friend.id }}</small>
                </button>
                <p>Tab completes the first result · Enter adds or creates</p>
              </div>
            </div>
          </section>

          <section v-if="!activeLinkedPhotos.length" class="edit-field">
            <label for="edit-parent">Parent photo</label>
            <div v-if="activeParentPhoto" class="edit-chips">
              <span class="edit-chip">
                #{{ activeParentPhoto.id }}
                <button type="button" aria-label="Remove parent photo" @click="setPhotoParent(activePhoto, null)">×</button>
              </span>
            </div>
            <div class="edit-autocomplete">
              <input
                id="edit-parent"
                v-model="parentPhotoEditQuery"
                type="text"
                inputmode="numeric"
                autocomplete="off"
                placeholder="Search photo #ID"
                @keydown.tab="autocompleteParentPhoto"
                @keydown.enter.prevent="commitParentPhoto"
              />
              <div v-if="parentPhotoEditQuery.trim()" class="edit-suggestions">
                <button
                  v-for="photo in parentPhotoEditSuggestions"
                  :key="photo.id"
                  class="edit-photo-suggestion"
                  type="button"
                  @mousedown.prevent="selectParentPhoto(photo)"
                >
                  <span>#{{ photo.id }}</span>
                  <img :src="thumbnailPath(photo.filename)" alt="" loading="lazy" />
                </button>
              </div>
            </div>
          </section>

          <section v-if="!activeParentPhoto" class="edit-field">
            <label for="edit-linked">Linked photos</label>
            <div class="edit-chips">
              <span v-for="photo in activeLinkedPhotos" :key="photo.id" class="edit-chip">
                #{{ photo.id }}
                <button type="button" :aria-label="`Remove photo #${photo.id}`" @click="removeLinkedPhoto(photo)">×</button>
              </span>
            </div>
            <div class="edit-autocomplete">
              <input
                id="edit-linked"
                v-model="linkedPhotoEditQuery"
                type="text"
                inputmode="numeric"
                autocomplete="off"
                placeholder="Add photo #ID"
                @keydown.tab="autocompleteLinkedPhoto"
                @keydown.enter.prevent="commitLinkedPhoto"
              />
              <div v-if="linkedPhotoEditQuery.trim()" class="edit-suggestions">
                <button
                  v-for="photo in linkedPhotoEditSuggestions"
                  :key="photo.id"
                  class="edit-photo-suggestion"
                  type="button"
                  @mousedown.prevent="addLinkedPhoto(photo)"
                >
                  <span>#{{ photo.id }}</span>
                  <img :src="thumbnailPath(photo.filename)" alt="" loading="lazy" />
                </button>
              </div>
            </div>
          </section>

          <section class="edit-field edit-field--tags">
            <label for="edit-tag-friend">Tags <small>Drag tags directly on the photo</small></label>
            <button
              class="edit-generate-tags"
              type="button"
              :disabled="!canGenerateCurrentPhotoTags"
              @click="generateCurrentPhotoTags"
            >
              {{ activePhotoTags.length ? 'Tags already exist' : activePhotoFriendIds.length ? 'Generate tags from friends' : 'No friends to generate tags' }}
            </button>
            <div class="edit-tag-list">
              <div v-for="tag in activePhotoTags" :key="`${tag.friendId}-${tag.index}`" class="edit-tag-row">
                <span>{{ tag.name }}</span>
                <button type="button" :aria-label="`Change ${tag.name} tag direction`" @click="cycleTagPosition(tag.index)">
                  {{ tagPositionLabels[tag.position] }}
                </button>
                <button type="button" :aria-label="`Delete ${tag.name} tag`" @click="removePhotoTag(tag.index)">×</button>
              </div>
            </div>
            <div class="edit-autocomplete">
              <input
                id="edit-tag-friend"
                v-model="tagFriendEditQuery"
                type="text"
                autocomplete="off"
                placeholder="Add a friend tag"
                @keydown.tab="autocompletePhotoTag"
                @keydown.enter.prevent="commitPhotoTag"
              />
              <div v-if="tagFriendEditQuery.trim()" class="edit-suggestions edit-suggestions--up">
                <button
                  v-for="friend in tagFriendEditSuggestions"
                  :key="friend.id"
                  type="button"
                  @mousedown.prevent="addPhotoTag(friend)"
                >
                  <span>{{ localisedText(friend.name_en, friend.name_zh) }}</span>
                  <small>{{ friend.id }}</small>
                </button>
                <p>New tags start in the centre with a BOTTOM label</p>
              </div>
            </div>
          </section>

          <footer class="edit-panel__footer">
            <p :class="`is-${editSaveState}`" aria-live="polite">{{ editSaveMessage || 'Changes are not saved automatically' }}</p>
            <button type="button" :disabled="editSaveState === 'saving'" @click="saveEditedGalleryData">
              {{ editSaveState === 'saving' ? 'Saving…' : 'Save all changes' }}
            </button>
          </footer>
          </template>
        </aside>

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
                :class="{ 'is-editing': editModeEnabled }"
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
                  @click.stop="editModeEnabled || applyFriendFilter(tag.friendId, true)"
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
                :class="{ 'description-emphasis': part.emphasis }"
                @click="applyFriendFilter(part.id, true)"
              >
                {{ part.name }}
              </button>
              <button
                v-else-if="part.type === 'world'"
                type="button"
                class="world-link"
                :class="{ 'description-emphasis': part.emphasis }"
                @click="applyWorldFilter(part.id, true)"
              >
                <span>{{ part.name }}</span>
              </button>
              <br v-else-if="part.type === 'break'" />
              <em v-else-if="part.emphasis">{{ part.text }}</em>
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
