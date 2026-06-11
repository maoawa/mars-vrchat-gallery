const TARGET_OFFSET_MINUTES = 8 * 60

const parseAsOffsetDate = (dateString: string) => {
  const hasTimeZone = /([zZ]|[+-]\d{2}:\d{2})$/.test(dateString)
  const withTime = dateString.includes('T') ? dateString : `${dateString}T00:00:00`
  const iso = hasTimeZone ? withTime : `${withTime}+08:00`

  const base = new Date(iso)
  // Shift so local getters reflect the target +08:00 wall-clock time regardless of viewer timezone.
  return new Date(base.getTime() + (TARGET_OFFSET_MINUTES + base.getTimezoneOffset()) * 60_000)
}

export default parseAsOffsetDate