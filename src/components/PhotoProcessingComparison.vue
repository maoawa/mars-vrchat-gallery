<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { processedPhotoPath } from '../utils/gallery'

const props = defineProps<{
  originalLabel: string
  processedLabel: string
  unavailableLabel: string
  caption: string
}>()

const comparisonPhotoId = 293
const comparisonFilename = 'VRChat_2026-10-11_03-47-50.jpg'
const split = ref(50)
let autoStartTimer: number | undefined
let animationFrame: number | undefined
let repeatTimer: number | undefined
let autoStopped = false
const originalUnavailable = ref(false)
const processedUnavailable = ref(false)
const splitStyle = computed(() => ({ '--comparison-split': `${split.value}%` }))
const originalSrc = '/photos/VRChat_2026-10-11_03-47-50.jpg'
const processedSrc = processedPhotoPath(comparisonFilename)

function stopAutoplay() {
  autoStopped = true
  if (autoStartTimer !== undefined) {
    window.clearTimeout(autoStartTimer)
    autoStartTimer = undefined
  }
  if (animationFrame !== undefined) {
    window.cancelAnimationFrame(animationFrame)
    animationFrame = undefined
  }
  if (repeatTimer !== undefined) {
    window.clearTimeout(repeatTimer)
    repeatTimer = undefined
  }
}

function easeInOut(value: number) {
  return value < 0.5 ? 2 * value * value : 1 - Math.pow(-2 * value + 2, 2) / 2
}

function animateSplit(from: number, to: number, duration: number, done: () => void) {
  const startedAt = performance.now()

  const frame = (now: number) => {
    if (autoStopped) return
    const progress = Math.min(1, (now - startedAt) / duration)
    split.value = from + (to - from) * easeInOut(progress)
    if (progress < 1) {
      animationFrame = window.requestAnimationFrame(frame)
    } else {
      animationFrame = undefined
      done()
    }
  }

  animationFrame = window.requestAnimationFrame(frame)
}

function runDemoSweep() {
  if (autoStopped) return
  animateSplit(split.value, 80, 1_700, () => {
    animateSplit(80, 20, 2_200, () => {
      animateSplit(20, 50, 1_700, () => {
        repeatTimer = window.setTimeout(() => {
          repeatTimer = undefined
          runDemoSweep()
        }, 1_500)
      })
    })
  })
}

onMounted(() => {
  autoStartTimer = window.setTimeout(runDemoSweep, 700)
})

onBeforeUnmount(stopAutoplay)
</script>

<template>
  <div>
    <div class="photo-comparison" :style="splitStyle">
      <img
        :class="{ 'is-unavailable': processedUnavailable }"
        class="photo-comparison__image photo-comparison__image--processed"
        :src="processedSrc"
        :alt="`${props.processedLabel} #${comparisonPhotoId}`"
        @error="processedUnavailable = true"
      />
      <div class="photo-comparison__original">
        <img
          :class="{ 'is-unavailable': originalUnavailable }"
          class="photo-comparison__image"
          :src="originalSrc"
          :alt="`${props.originalLabel} #${comparisonPhotoId}`"
          @error="originalUnavailable = true"
        />
      </div>
      <div class="photo-comparison__divider" aria-hidden="true"></div>
      <div class="photo-comparison__labels" aria-hidden="true">
        <span>{{ props.originalLabel }}</span>
        <span>{{ props.processedLabel }}</span>
      </div>
      <input
        v-model.number="split"
        class="photo-comparison__range"
        @pointerdown="stopAutoplay"
        @touchstart="stopAutoplay"
        @focus="stopAutoplay"
        type="range"
        min="0"
        max="100"
        step="1"
        :aria-label="`${props.originalLabel} / ${props.processedLabel}`"
      />
      <p v-if="originalUnavailable || processedUnavailable" class="photo-comparison__unavailable">
        {{ props.unavailableLabel }}
      </p>
    </div>
  </div>
</template>
