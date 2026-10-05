# React frontend

The contact form uses React 19, TypeScript and Vite. CSS, fonts and assets are
served locally, without jQuery or a CDN. Labels, native validation, visible focus,
responsive layout and live feedback support keyboard and mobile use. Sending
blocks duplicate submissions; successful responses clear the form, while failures
preserve the input. Requests have a ten-second timeout and are not automatically
retried, because the server does not support idempotency keys.

## Request path and compatibility

The public `php` LoadBalancer Service now selects the `frontend` Deployment
(two Nginx replicas). Nginx serves the compiled files and forwards exact
`/index.php` and `/health.php` requests to the internal `php-backend` Service,
which selects the six PHP replicas. MySQL, the PVC, Secrets and field names remain
unchanged. External URLs and `kubectl port-forward service/php 8080:80` still work.

POST `/index.php` continues to accept URL-encoded `nome`, `email` and `comentario`,
with limits of 50, 50 and 100 characters. Status codes and response text are
unchanged. GET `/index.php` is proxied to PHP, which also has the same compiled
bundle and assets for direct GET compatibility. GET `/` serves the React shell;
JavaScript is now required to render the form. Old `/css.css` and `/js.js` assets
are removed in favor of Vite's hashed assets. Unknown paths return 404.

Nginx startup/liveness check static GET `/`; readiness proxies `/health.php`.
Its two replicas each request 50m CPU/64Mi memory and allow 250m CPU/128Mi memory.
These are initial demonstration values. If PHP or MySQL is unavailable, readiness
fails while Nginx remains alive. A 16KiB request-body limit rejects oversized
payloads with 413. Default frontend `PHP_UPSTREAM=php-backend:80` can be overridden
when launching the Docker image on another network; it is not a browser setting.
No CORS configuration is needed for this same-origin deployment.

## Builds and development

Both frontend and backend Dockerfiles use the same pinned Node 24 build stage,
`npm ci --ignore-scripts` with a committed lockfile and `npm run build`. Nginx and
PHP runtime images receive only compiled assets; Node and development dependencies
remain in the build stage. Including the bundle in PHP preserves its existing GET
behavior. MySQL builds independently. Registry scripts tag, publish and roll out
all three images. Local kind deployment loads all three images without a registry.

For host development, install Node 24, then run `make frontend-setup`. Use
`make frontend-check` for TypeScript and production build and `make frontend-test`
for component tests. With the local cluster deployed, keep `make access` running
and run `make frontend-dev` in another terminal. Vite proxies PHP requests to port
8080; change its proxy configuration if you choose a different access port.

## Browser tests

Install Chromium after frontend dependencies:

```sh
make frontend-browser-setup
```

Linux shared libraries required by Playwright must be installed. CI installs them
with `playwright install --with-deps chromium`; a host installation is not changed
by the Makefile. Chromium normally downloads to the user's Playwright cache; set
`PLAYWRIGHT_BROWSERS_PATH` consistently to use another directory.

Run `make frontend-browser` against the running application, with the access
tunnel on port 8080. Override `BASE_URL` to target another disposable application.
The tests create one message and should only target test data. They cover real
submission, native email validation, simulated HTTP 503 feedback, mobile overflow
and keyboard focus. A simulated response tests the UI's error handling; it is not
a real cluster outage test.

The Python integration suite runs these four browser checks against its isolated
Docker application and verifies that the submitted message exists in MySQL. The
suite requires Node 24, installed frontend dependencies and Chromium. CI runs
component tests, browser checks, builds and existing API/deployment checks.

## Validation

On 2026-10-05 (America/Belem), TypeScript and production builds, eight component
tests and all 22 Python tests passed. The Python suite includes four Chromium
scenarios and confirms browser submission in MySQL. The three Docker images,
PHP syntax, source/rendered Kubernetes schemas and actionlint passed. Deployment
on the existing kind cluster reached two ready Nginx replicas, six ready PHP
replicas and one ready MySQL replica. The original PVC remained bound. Cluster
smoke checks confirmed persistence after MySQL pod replacement; the four browser
scenarios also passed against kind. Desktop/mobile screenshots were visually
inspected. The updated workflow has been linted locally; its actual GitHub run
must be checked after publication.

No production deployment or image
publication is performed during this phase. WSL, other browser engines, load,
TLS termination and production authentication remain outside this validation.
