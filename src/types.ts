export interface Friend {
  id: string
  name: string
}

export interface World {
  id: string
  name: string
}

export interface GalleryImage {
  id: number
  filename: string
  captured: string
  world: string
  description: string
  friend: string[]
  linked?: number[]
  parent?: number
}

export interface GalleryRow {
  photo: GalleryImage
  linkedPhotos: GalleryImage[]
}
