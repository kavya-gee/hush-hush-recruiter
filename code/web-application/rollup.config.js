import { nodeResolve } from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';

export default {
  input: 'core/static/core/js/assessment_workspace.js',
  output: {
    file: 'core/static/core/js/bundle.js',
    format: 'iife',
    sourcemap: true
  },
  plugins: [
    nodeResolve(),
    commonjs()
  ]
};