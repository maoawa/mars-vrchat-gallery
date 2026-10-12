import { parseAsGalleryDate } from './date'
import { mirrorAssetBase, photoAssetFilename, photoAssetUrl } from './photo-assets'

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

const zhDateFormatter = new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric',
  month: 'long',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
  hour12: true,
})

const vrchatStartUtc = Date.UTC(2026, 5, 3, 18, 0, 0)
const millisecondsPerDay = 24 * 60 * 60 * 1000

const assetBaseUrl = mirrorAssetBase

export function originalPhotoFilename(filename: string) {
  return photoAssetFilename(filename, 'png')
}

export function photoPath(filename: string) {
  return photoAssetUrl(assetBaseUrl, 'full', filename)
}

export function thumbnailPath(filename: string) {
  return photoAssetUrl(assetBaseUrl, 'thumbnail', filename)
}

export function processedPhotoPath(filename: string) {
  return photoAssetUrl(assetBaseUrl, 'full', filename)
}

export function remoteOriginalPhotoPath(filename: string) {
  return photoAssetUrl(assetBaseUrl, 'original', filename)
}

export function originalPhotoPath(filename: string) {
  return photoAssetUrl(assetBaseUrl, 'original', filename)
}

export function formatGalleryDate(capturedAt: string, language: 'en' | 'zh' = 'en') {
  const date = parseAsGalleryDate(capturedAt)

  if (language === 'zh') {
    return zhDateFormatter.format(date)
  }

  const month = monthNames[date.getMonth()]
  const day = date.getDate()
  const year = date.getFullYear()
  const hours = date.getHours()
  const minutes = date.getMinutes()
  const meridiem = hours >= 12 ? 'PM' : 'AM'
  const hour12 = hours % 12 || 12

  return `${month} ${day}, ${year} at ${hour12}:${String(minutes).padStart(2, '0')} ${meridiem}`
}

export function daysSinceVrchatStart(now = Date.now()) {
  return Math.max(0, Math.floor((now - vrchatStartUtc) / millisecondsPerDay))
}
