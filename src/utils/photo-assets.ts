export const mirrorAssetBase = 'https://r2.vrchat.marsinside.com'

export function photoAssetFilename(filename: string, extension: 'jpg' | 'png') {
  return filename.replace(/\.(?:png|jpe?g)$/i, `.${extension}`)
}

export function photoAssetUrl(base: string, variant: 'original' | 'full' | 'thumbnail', filename: string) {
  const extension = variant === 'original' ? 'png' : 'jpg'
  return `${base.replace(/\/+$/, '')}/${variant}/${encodeURIComponent(photoAssetFilename(filename, extension))}`
}

export function galleryRouteTarget(pathname: string, hash: string) {
  // Hash links (including friend/world filters) take priority over a photo path.
  try {
    const fragment = decodeURIComponent(hash.replace(/^#/, '')).trim()
    if (fragment) return fragment
    const path = pathname.replace(/^\/+|\/+$/g, '')
    return path && path !== 'statistics' ? path : ''
  } catch {
    // A malformed percent-escape should not prevent the gallery from mounting.
    return ''
  }
}
