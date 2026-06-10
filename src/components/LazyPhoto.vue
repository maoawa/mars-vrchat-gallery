<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps<{
  src: string
  alt: string
  eager?: boolean
}>()

const wrapper = ref<HTMLElement | null>(null)
const shouldLoad = ref(Boolean(props.eager))
const hasLoaded = ref(false)
const aspectRatio = ref('16 / 9')

let observer: IntersectionObserver | undefined

onMounted(() => {
  if (shouldLoad.value) {
    return
  }

  if (!('IntersectionObserver' in window)) {
    shouldLoad.value = true
    return
  }

  observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        shouldLoad.value = true
        observer?.disconnect()
      }
    },
    {
      rootMargin: '420px 0px',
      threshold: 0.01,
    },
  )

  if (wrapper.value) {
    observer.observe(wrapper.value)
  }
})

onBeforeUnmount(() => {
  observer?.disconnect()
})

function handleLoad(event: Event) {
  const image = event.currentTarget as HTMLImageElement

  if (image.naturalWidth && image.naturalHeight) {
    aspectRatio.value = `${image.naturalWidth} / ${image.naturalHeight}`
  }

  hasLoaded.value = true
}
</script>

<template>
  <span
    ref="wrapper"
    class="lazy-photo"
    :class="{ 'is-loaded': hasLoaded }"
    :style="{ aspectRatio }"
  >
    <img
      v-if="shouldLoad"
      :src="src"
      :alt="alt"
      :loading="eager ? 'eager' : 'lazy'"
      decoding="async"
      @load="handleLoad"
    />
    <span v-if="!hasLoaded" class="lazy-photo__placeholder" aria-hidden="true"></span>
  </span>
</template>

<style scoped>
.lazy-photo {
  position: relative;
  display: block;
  width: 100%;
  overflow: hidden;
  background: #171719;
}

.lazy-photo img,
.lazy-photo__placeholder {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.lazy-photo img {
  object-fit: cover;
  opacity: 0;
  transform: scale(1.018);
  transition:
    opacity 360ms ease,
    transform 700ms ease;
}

.lazy-photo.is-loaded img {
  opacity: 1;
  transform: scale(1);
}

.lazy-photo__placeholder {
  background:
    linear-gradient(110deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.04)),
    #171719;
  background-size: 220% 100%;
  animation: photo-placeholder 1.4s ease-in-out infinite;
}

@keyframes photo-placeholder {
  from {
    background-position: 120% 0;
  }

  to {
    background-position: -120% 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .lazy-photo img,
  .lazy-photo__placeholder {
    animation: none;
    transition: none;
  }
}
</style>
