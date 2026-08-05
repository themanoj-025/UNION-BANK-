module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'scope-case': [2, 'always', 'kebab-case'],
    'subject-case': [2, 'never', ['sentence-case', 'start-case']],
    'header-max-length': [2, 'always', 100],
    // Dependabot auto-generated commit bodies contain upstream changelog
    // excerpts that regularly exceed 100 chars per line and cannot be
    // rewritten. Disable the body line-length rule so Dependabot PRs are
    // not blocked by their own release notes.
    'body-max-line-length': [0, 'always', 100],
  },
};
