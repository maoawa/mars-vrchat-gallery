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

const vrchatStartUtc = Date.UTC(2026, 5, 3, 18, 0, 0)
const millisecondsPerDay = 24 * 60 * 60 * 1000

export function photoPath(filename: string) {
  return `/photos/${filename}`
}

export function thumbnailPath(filename: string) {
  return `/photos/thumbnails/${filename}`
}

export function formatGalleryDate(capturedAt: string) {
  const [datePart, timePart = '00:00:00'] = capturedAt.split('T')
  const [year, month, day] = datePart.split('-').map(Number)
  const [hours = 0, minutes = 0] = timePart.split(':').map(Number)
  const meridiem = hours >= 12 ? 'PM' : 'AM'
  const hour12 = hours % 12 || 12

  return `${monthNames[month - 1]} ${day} ${year} at ${hour12}:${String(minutes).padStart(2, '0')} ${meridiem}`
}

export function daysSinceVrchatStart(now = Date.now()) {
  return Math.max(0, Math.floor((now - vrchatStartUtc) / millisecondsPerDay))
}
