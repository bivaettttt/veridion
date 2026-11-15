import eslint from '@eslint/js'
import typescript from 'typescript-eslint'

export default typescript.config(eslint.configs.recommended, ...typescript.configs.recommended)
