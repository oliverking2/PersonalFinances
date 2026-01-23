// @ts-check
import withNuxt from './.nuxt/eslint.config.mjs'

export default withNuxt({
  rules: {
    // Allow Prettier's self-closing style on void elements
    'vue/html-self-closing': [
      'error',
      {
        html: {
          void: 'any', // <input> or <input /> both allowed
          normal: 'always',
          component: 'always',
        },
      },
    ],
  },
})
