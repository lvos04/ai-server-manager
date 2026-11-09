// ESLint (flat config): Next.js core-web-vitals + TypeScript + strengere toegankelijkheidsregels (jsx-a11y).
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import jsxA11y from "eslint-plugin-jsx-a11y";

const config = [
  ...nextVitals,
  ...nextTs,
  {
    files: ["**/*.{ts,tsx}"],
    rules: {
      ...jsxA11y.flatConfigs.strict.rules,
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/consistent-type-imports": "error",
    },
  },
  {
    ignores: [".next/**", "node_modules/**", "test-results/**", "playwright-report/**", "next-env.d.ts", "public/sw.js"],
  },
];

export default config;
