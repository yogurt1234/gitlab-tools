// eslint.config.cjs

/**
 * Flat-config 用設定ファイル
 * - eslint:recommended を jsConfigs.recommended として適用
 * - Vue3 推奨設定を vueConfigs['vue3-recommended'] として適用
 * - overrides キーや extends キーは使わず、設定オブジェクト配列で定義
 */

const { configs: jsConfigs } = require("@eslint/js");
const vuePlugin = require("eslint-plugin-vue");
const { configs: vueConfigs } = vuePlugin;
const vueParser = require("vue-eslint-parser");
const babelParser = require("@babel/eslint-parser");

module.exports = [
  // 全ファイル共通: eslint:recommended
  jsConfigs.recommended,

  // Vue ファイル向け: Vue3 推奨設定 + SFC パース
  {
    files: ["**/*.vue"],

    languageOptions: {
      parser: require("vue-eslint-parser"),
      parserOptions: {
        // Babel parser に設定ファイル不要モードを指定
        parser: "@babel/eslint-parser",
        requireConfigFile: false,
        babelOptions: {
          presets: ["@babel/preset-env"], // 必要に応じて追加
        },
        ecmaVersion: 2021,
        sourceType: "module",
      },
    },

    plugins: {
      vue: require("eslint-plugin-vue"),
    },

    // Vue3 推奨設定を展開
    ...require("eslint-plugin-vue").configs["vue3-recommended"],
  },
];
