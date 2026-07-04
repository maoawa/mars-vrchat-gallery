export type Language = 'en' | 'zh'

export const languageCopy = {
  en: {
    title: 'Mars VRChat Gallery',
    languageToggle: '中文',
    languageLabel: 'Switch language to Chinese',
    introBeforeLink:
      "Hi! I'm Mars. As you can see, this is my personal VRChat gallery. It's still under construction so I may forget to mention some friends. But I didn't mean to ignore them, and I do cherish every friends of mine. Please contact me using methods in ",
    introAfterLink:
      ' or buttons at the bottom or in game. Thanks for appearing in my life and I love you guys!',
    randomMemory: 'Random memory',
    specialEvent: 'Special event',
    showing: 'Showing',
    for: 'for',
    outing: 'outing',
    outings: 'outings',
    clear: 'Clear',
    with: 'With',
    photos: 'photos',
    footerDaysBefore: '',
    footerDaysAfter: ' days since Mars joined VRChat',
    zoom: 'Zoom',
    close: 'Close',
    previous: 'Previous photo',
    next: 'Next photo',
    open: 'Open',
    showTags: 'Show Tags',
    showTagsLabel: 'Show photo tags',
    toggleTagsHint: 'Toggle tags here',
    taggedFriends: 'Tagged friends',
    wechat: 'WeChat',
    qq: 'QQ',
    copyright: '© 2026 Mars. All rights reserved.',
  },
  zh: {
    title: '毛毛的 VRChat 相册',
    languageToggle: 'English',
    languageLabel: '切换语言为英语',
    introBeforeLink:
      '嗨！我是毛毛(Mars)。正如你所见，这是我的个人 VRChat 相册。这里仍在建设中，所以我可能会不小心漏掉一些朋友。但我绝不是有意忽略他们，我真心珍视我的每一位朋友。请通过 ',
    introAfterLink:
      ' 上的方式或底部的按钮，或直接在游戏里联系我。感谢你们出现在我的生活中，我爱你们！',
    randomMemory: '随机回忆',
    specialEvent: '特别事件',
    showing: '正在显示',
    for: '关于',
    outing: '个聚会',
    outings: '个聚会',
    clear: '清除',
    with: '与',
    photos: '张照片',
    footerDaysBefore: '毛毛加入 VRChat ',
    footerDaysAfter: ' 天了',
    zoom: '缩放',
    close: '关闭',
    previous: '上一张照片',
    next: '下一张照片',
    open: '打开',
    showTags: '显示标记',
    showTagsLabel: '显示照片标记',
    toggleTagsHint: '在这里切换标记显示',
    taggedFriends: '已标记的朋友',
    wechat: '微信',
    qq: 'QQ',
    copyright: '© 2026 毛毛 (Mars) 保留所有权利',
  },
} satisfies Record<Language, Record<string, string>>

export function detectPreferredLanguage(): Language {
  if (typeof window === 'undefined') {
    return 'en'
  }

  const savedLanguage = window.localStorage.getItem('gallery-language')
  if (savedLanguage === 'zh' || savedLanguage === 'en') {
    return savedLanguage
  }

  const browserLanguages =
    window.navigator.languages.length > 0 ? window.navigator.languages : [window.navigator.language]

  return browserLanguages.some((language) => language.toLowerCase().startsWith('zh')) ? 'zh' : 'en'
}
