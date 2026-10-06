const GALLERY_TIMEZONE_OFFSET_MINUTES = 8 * 60

export function parseAsGalleryDate(dateString: string) {
  const hasTimeZone = /([zZ]|[+-]\d{2}:\d{2})$/.test(dateString)
  const withTime = dateString.includes('T') ? dateString : `${dateString}T00:00:00`
  const iso = hasTimeZone ? withTime : `${withTime}+08:00`

  const base = new Date(iso)

  // Keep gallery timestamps as GMT+8 wall-clock time, regardless of the viewer's timezone.
  return new Date(
    base.getTime() + (GALLERY_TIMEZONE_OFFSET_MINUTES + base.getTimezoneOffset()) * 60_000,
  )
}
