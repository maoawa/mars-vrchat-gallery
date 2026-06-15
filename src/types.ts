export interface Friend {
  id: string
  name_en: string
  name_zh?: string
}

export interface World {
  id: string
  name_en: string
  name_zh?: string
}

export interface GalleryImage {
  id: number
  filename: string
  captured: string
  world: string
  'special-events'?: boolean
  description_en?: string
  description_zh?: string
  friend: string[]
  linked?: number[]
  parent?: number
}

export interface GalleryRow {
  photo: GalleryImage
  linkedPhotos: GalleryImage[]
}

export interface SpecialEvent {
  id: string
  title_en: string
  title_zh?: string
  date_en: string
  date_zh?: string
  show_full_date?: boolean
  world?: string
  friends?: string[]
  description_en?: string
  description_zh?: string
  photo_ids: number[]
  featured_photo_ids: number[]
}
