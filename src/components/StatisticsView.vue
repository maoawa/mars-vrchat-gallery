<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import friendsData from '../data/friends.json'
import imagesData from '../data/images.json'
import specialEventsData from '../data/special-events.json'
import worldsData from '../data/worlds.json'
import statisticsConfig from '../statistics.json'
import type { Friend, GalleryImage, SpecialEvent, World } from '../types'
import type { Language } from '../i18n'

const props = defineProps<{ language: Language }>()

type Metric = 'outings' | 'pictures'
type RankedItem = {
  id: string
  name: string
  outings: number
  pictures: number
}

const friends = friendsData as Friend[]
const worlds = worldsData as World[]
const photos = imagesData as GalleryImage[]
const events = specialEventsData as SpecialEvent[]
const metric = ref<Metric>('outings')
const mobileHours = Number((statisticsConfig as { mobileHours?: number }).mobileHours) || 0
const showMobileHours = (statisticsConfig as { 'show-mobile-hours'?: boolean })['show-mobile-hours'] !== false
const steamHours = ref<number | null>(null)
const steamStatus = ref<'idle' | 'loading' | 'ready' | 'unavailable'>('idle')
const steamApiUrl =
  (statisticsConfig as { steamApiEndpoint?: string }).steamApiEndpoint ||
  import.meta.env.VITE_STEAM_API_URL ||
  '/api/steam-playtime'

const ordinaryOutings = photos
  .filter((photo) => !photo.parent && !photo['special-events'])
  .map((photo) => ({
    photos: [photo, ...(photo.linked ?? []).map((id) => photos.find((candidate) => candidate.id === id)).filter((photo): photo is GalleryImage => Boolean(photo))],
  }))

const eventOutings = events
  .map((event) => ({
    event,
    photos: event.photo_ids.map((id) => photos.find((photo) => photo.id === id)).filter((photo): photo is GalleryImage => Boolean(photo)),
  }))
  .filter((outing) => outing.photos.length > 0)

function displayName(entity: Friend | World) {
  return props.language === 'zh' ? entity.name_zh || entity.name_en : entity.name_en
}

function rankFriends(): RankedItem[] {
  return friends
    .map((friend) => {
      let outings = 0
      let pictures = 0

      ordinaryOutings.forEach((outing) => {
        if (outing.photos.some((photo) => photo.friend.includes(friend.id))) {
          outings += 1
          pictures += outing.photos.filter((photo) => photo.friend.includes(friend.id)).length
        }
      })

      eventOutings.forEach(({ event, photos: eventPhotos }) => {
        if ((event.friends ?? []).includes(friend.id) || eventPhotos.some((photo) => photo.friend.includes(friend.id))) {
          outings += 1
          pictures += eventPhotos.filter((photo) => (event.friends ?? []).includes(friend.id) || photo.friend.includes(friend.id)).length
        }
      })

      return { id: friend.id, name: displayName(friend), outings, pictures }
    })
    .filter((item) => item.outings > 0)
    .sort((a, b) => b[metric.value] - a[metric.value] || a.name.localeCompare(b.name))
}

function rankWorlds(): RankedItem[] {
  return worlds
    .map((world) => {
      let outings = 0
      let pictures = 0

      ordinaryOutings.forEach((outing) => {
        const worldPhotos = outing.photos.filter((photo) => photo.world === world.id)
        if (worldPhotos.length) {
          outings += 1
          pictures += worldPhotos.length
        }
      })

      eventOutings.forEach(({ event, photos: eventPhotos }) => {
        const worldPhotos = eventPhotos.filter((photo) => photo.world === world.id)
        if (event.world === world.id || worldPhotos.length) {
          outings += 1
          pictures += event.world === world.id ? eventPhotos.length : worldPhotos.length
        }
      })

      return { id: world.id, name: displayName(world), outings, pictures }
    })
    .filter((item) => item.outings > 0)
    .sort((a, b) => b[metric.value] - a[metric.value] || a.name.localeCompare(b.name))
}

const friendRanking = computed(rankFriends)
const worldRanking = computed(rankWorlds)
const friendMaximum = computed(() => Math.max(1, ...friendRanking.value.map((item) => item[metric.value])))
const worldMaximum = computed(() => Math.max(1, ...worldRanking.value.map((item) => item[metric.value])))
const totalHours = computed(() => (steamHours.value ?? 0) + (showMobileHours ? mobileHours : 0))
const copy = computed(() =>
  props.language === 'zh'
    ? {
        title: '统计',
        brand: 'Mars VRChat Gallery',
        sortBy: '排序方式',
        subtitle: '按朋友和世界查看一起度过的时光。',
        outings: '聚会',
        photos: '照片',
        friends: '朋友',
        worlds: '世界',
        rank: '排名',
        count: '数量',
        back: '返回相册',
        language: 'English',
        outingsHint: '每次聚会只计算一次',
        picturesHint: '按相关照片数量计算',
        mobile: 'Mobile',
        steam: 'Steam',
        totalHours: '总小时数',
        steamUnavailable: 'Steam 数据暂不可用',
        steamLoading: '正在读取 Steam 数据…',
      }
    : {
        title: 'Statistics',
        brand: 'Mars VRChat Gallery',
        sortBy: 'Sort by',
        subtitle: 'See which friends and worlds appear most often in shared memories.',
        outings: 'Outings',
        photos: 'Photos',
        friends: 'Friends',
        worlds: 'Worlds',
        rank: 'Rank',
        count: 'Count',
        back: 'Back to gallery',
        language: '中文',
        outingsHint: 'Each outing counts once',
        picturesHint: 'Counts related pictures',
        mobile: 'Mobile',
        steam: 'Steam',
        totalHours: 'Total hours',
        steamUnavailable: 'Steam data is unavailable',
        steamLoading: 'Loading Steam data…',
      },
)

function barWidth(item: RankedItem, maximum: number) {
  return `${Math.max(2, (item[metric.value] / maximum) * 100)}%`
}

function steamStatusText() {
  if (steamStatus.value === 'loading') return copy.value.steamLoading
  if (steamStatus.value === 'unavailable') return copy.value.steamUnavailable
  return ''
}

onMounted(async () => {
  steamStatus.value = 'loading'

  try {
    const response = await fetch(steamApiUrl)
    if (!response.ok) throw new Error('Steam endpoint unavailable')
    const payload = (await response.json()) as { playtimeHours?: number }
    if (typeof payload.playtimeHours !== 'number') throw new Error('Steam playtime missing')
    steamHours.value = payload.playtimeHours
    steamStatus.value = 'ready'
  } catch {
    steamStatus.value = 'unavailable'
  }
})
</script>

<template>
  <main class="site-shell statistics-page">
    <header class="statistics-header">
      <div class="statistics-topbar">
        <a class="statistics-back" href="/">← {{ copy.back }}</a>
      </div>
      <p class="statistics-eyebrow statistics-brand">{{ copy.brand }}</p>
      <h1 class="statistics-title">{{ copy.title }}</h1>
  </header>

  <section class="statistics-hours" :class="{ 'statistics-hours--compact': !showMobileHours }" aria-labelledby="hours-heading">
    <div>
      <p class="statistics-eyebrow">VRCHAT PLAYTIME</p>
      <h2 id="hours-heading">{{ totalHours.toFixed(1) }} h</h2>
      <p v-if="steamStatusText()" class="statistics-hours__status">{{ steamStatusText() }}</p>
    </div>
    <dl v-if="showMobileHours" class="statistics-hours__breakdown">
      <div>
        <dt>{{ copy.steam }}</dt>
        <dd>{{ steamHours === null ? '—' : `${steamHours.toFixed(1)} h` }}</dd>
      </div>
      <div>
        <dt>{{ copy.mobile }}</dt>
        <dd>
          {{ mobileHours.toFixed(1) }} h
        </dd>
      </div>
    </dl>
  </section>

  <p class="statistics-subtitle">{{ copy.subtitle }}</p>

  <div class="statistics-sort-row">
      <span>{{ copy.sortBy }}</span>
      <div class="statistics-toggle" role="group" :aria-label="copy.sortBy">
      <button type="button" :class="{ active: metric === 'outings' }" @click="metric = 'outings'">
        {{ copy.outings }}
      </button>
      <button type="button" :class="{ active: metric === 'pictures' }" @click="metric = 'pictures'">
        {{ copy.photos }}
      </button>
      </div>
    </div>

    <div class="statistics-grid">
      <section class="statistics-card" aria-labelledby="friends-heading">
        <div class="statistics-card__heading">
          <h2 id="friends-heading">{{ copy.friends }}</h2>
        </div>
        <ol class="statistics-list">
          <li v-for="(item, index) in friendRanking" :key="item.id">
            <span class="statistics-rank">{{ index + 1 }}</span>
            <a class="statistics-name statistics-link" :href="`/?from=statistics#friend=${encodeURIComponent(item.id)}`">{{ item.name }}</a>
            <span class="statistics-bar-track" aria-hidden="true"><span class="statistics-bar" :style="{ width: barWidth(item, friendMaximum) }"></span></span>
            <strong class="statistics-value">{{ item[metric] }}</strong>
          </li>
        </ol>
      </section>

      <section class="statistics-card" aria-labelledby="worlds-heading">
        <div class="statistics-card__heading">
          <h2 id="worlds-heading">{{ copy.worlds }}</h2>
        </div>
        <ol class="statistics-list">
          <li v-for="(item, index) in worldRanking" :key="item.id">
            <span class="statistics-rank">{{ index + 1 }}</span>
            <a class="statistics-name statistics-link" :href="`/?from=statistics#world=${encodeURIComponent(item.id)}`">{{ item.name }}</a>
            <span class="statistics-bar-track" aria-hidden="true"><span class="statistics-bar" :style="{ width: barWidth(item, worldMaximum) }"></span></span>
            <strong class="statistics-value">{{ item[metric] }}</strong>
          </li>
        </ol>
      </section>
    </div>
  </main>
</template>
