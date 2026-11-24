import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import quality from "./eslint-rules/index.cjs";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    files: ["eslint-rules/**/*.cjs"],
    rules: { "@typescript-eslint/no-require-imports": "off" },
  },
  {
    files: ["src/**/*.{js,jsx,ts,tsx}"],
    plugins: { quality },
    rules: {
      "quality/max-lines": ["error", { max: 800 }],
      "quality/no-direct-console": ["error", { allow: ["error", "warn"] }],
    },
  },
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "coverage/**",
    "test-results/**",
    "next-env.d.ts",
    ".agents/**",
  ]),
]);

export default eslintConfig;
