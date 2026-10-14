import { createRequire } from 'node:module';
import { writeFile } from 'node:fs/promises';

// The image installs Verdaccio globally. /opt/verdaccio only contains docker-bin,
// so resolving from this file's path cannot see bcryptjs.
const require = createRequire('/usr/local/lib/node_modules/verdaccio/package.json');
const bcrypt = require('bcryptjs');

const env = process.env;
const password = env.VERDACCIO_PASSWORD ?? '';
const username = env.VERDACCIO_USER || 'admin';
const internalUrl = (env.VERDACCIO_INTERNAL_URL || '').trim();

if (!password) {
  throw new Error('VERDACCIO_PASSWORD must be set before starting Verdaccio');
}

const uplinks = {
  npmjs: { url: 'https://registry.npmjs.org/' },
  github: {
    url: 'https://npm.pkg.github.com',
    auth: { type: 'bearer', token_env: 'VERDACCIO_GITHUB_TOKEN' },
  },
  gitlab: {
    url: env.VERDACCIO_GITLAB_URL || 'https://gitlab.com/api/v4/packages/npm/',
    auth: { type: 'bearer', token_env: 'VERDACCIO_GITLAB_TOKEN' },
  },
};

if (internalUrl) {
  uplinks.internal = {
    url: internalUrl,
    auth: { type: 'bearer', token_env: 'VERDACCIO_INTERNAL_TOKEN' },
  };
}

const packages = {};
const seenScopes = new Set();
const addScopeRules = (variable, uplink) => {
  if (!uplinks[uplink]) return;

  for (const rawScope of (env[variable] || '').split(',')) {
    const scope = rawScope.trim().replace(/^@/, '');
    if (!scope || seenScopes.has(scope)) continue;

    seenScopes.add(scope);
    packages[`@${scope}/*`] = {
      access: '$all',
      publish: '$authenticated',
      unpublish: '$authenticated',
      proxy: uplink,
    };
  }
};

addScopeRules('VERDACCIO_GITHUB_SCOPES', 'github');
addScopeRules('VERDACCIO_GITLAB_SCOPES', 'gitlab');
addScopeRules('VERDACCIO_INTERNAL_SCOPES', 'internal');

packages['@*/*'] = {
  access: '$all',
  publish: '$authenticated',
  unpublish: '$authenticated',
  proxy: 'npmjs',
};
packages['**'] = {
  access: '$all',
  publish: '$authenticated',
  unpublish: '$authenticated',
  proxy: 'npmjs',
};

const config = {
  listen: '0.0.0.0:4873',
  storage: '/verdaccio/storage',
  auth: {
    htpasswd: {
      file: '/verdaccio/conf/htpasswd',
      max_users: -1,
    },
  },
  uplinks,
  packages,
  log: { type: 'stdout', format: 'pretty', level: 'http' },
};

const hash = await bcrypt.hash(password, 10);
await writeFile('/verdaccio/conf/config.yaml', `${JSON.stringify(config, null, 2)}\n`, {
  mode: 0o600,
});
await writeFile('/verdaccio/conf/htpasswd', `${username}:${hash}\n`, {
  mode: 0o600,
});
