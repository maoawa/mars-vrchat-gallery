export type Language = 'en' | 'zh'

export const languageCopy = {
  en: {
    title: 'Mars VRChat Gallery',
    languageToggle: '中文',
    languageLabel: 'Switch language to Chinese',
    introShort:
      'If you find yourself in a photo but are not listed, please contact me, and please know it was not intentional.',
    introBeforeLink:
      "Hi, I'm Mars, and this is my personal VRChat gallery. It is still growing, so I may occasionally miss a friend's name or forget to list someone in a photo. If that happens, please contact me through ",
    introAfterLink:
      ', the links below, or in game. It was never intentional. I treasure every friend and every memory here and thank you for being part of my life!',
    introMore: 'More...',
    introLess: 'Hide',
    introDismiss: "Don't show this again",
    socialLinksLabel: 'Social links',
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
    lastUpdated: 'Last Updated',
    photoTimesNote: 'Photo times are shown in China Standard Time (UTC+8).',
    copyrightBeforeLink: '© 2026 Mars.',
    copyrightAfterLink: 'All rights reserved.',
  },
  zh: {
    title: '毛毛的 VRChat 相册',
    languageToggle: 'English',
    languageLabel: '切换语言为英语',
    introShort: '如果你发现自己出现在照片里但没有被列出，请联系我，也请相信我不是故意的。',
    introBeforeLink:
      '嗨！我是毛毛 (Mars)，这里是我的个人 VRChat 相册。它还在慢慢整理中，所以我有时可能会漏掉朋友的名字，或没有把照片里的人标完整。如果你发现这种情况，请通过 ',
    introAfterLink:
      '、下面的联系方式，或直接在游戏里联系我。这绝不是有意忽略你。我很珍惜这里的每位朋友和每段回忆，谢谢你们出现在我的生活里！',
    introMore: '更多...',
    introLess: '收起',
    introDismiss: '不再显示这个提示',
    socialLinksLabel: '社交链接',
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
    lastUpdated: '最后更新',
    photoTimesNote: '图片拍摄时间以中国标准时间显示 (UTC+8)',
    copyrightBeforeLink: '© 2026 毛毛 (Mars).',
    copyrightAfterLink: '保留所有权利',
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
