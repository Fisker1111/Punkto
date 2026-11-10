# www candidates — validation only

These fragments are candidates for founder approval, not deployed configuration.
The live `~/punkto/Caddyfile` is not to be edited by this PR. Neither artifact is a
whole-file replacement. All production execution, including the commands below,
requires separate explicit founder authorization. See the
[ordered runbook](../../../docs/operator/www-round-robin-runbook.md).

Each node's own issued certificate must already be readable at
`/etc/caddy/www-tls/fullchain.pem` and `/etc/caddy/www-tls/key.pem` inside its Caddy
container. Validation fails if those files/mounts are absent; do not bypass this
with a public automatic issuer or borrow another node's key.

From the reviewed checkout on **node1**, validation only:

```bash
docker cp deploy/candidate/www/node1.Caddyfile.www punkto-web-1:/tmp/node1.Caddyfile.www
docker exec punkto-web-1 caddy validate --config /tmp/node1.Caddyfile.www --adapter caddyfile
```

On **node2**, validation only:

```bash
docker cp deploy/candidate/www/node2.Caddyfile.www punkto-web-1:/tmp/node2.Caddyfile.www
docker exec punkto-web-1 caddy validate --config /tmp/node2.Caddyfile.www --adapter caddyfile
```

Expected exit 0 and `Valid configuration`; no reload/start/stop occurs. After the
operator prepares a complete `/tmp/Caddyfile.www-proposed` by replacing only the
live www block, validate that too on each node:

```bash
docker cp /tmp/Caddyfile.www-proposed punkto-web-1:/tmp/Caddyfile.www-proposed
docker exec punkto-web-1 caddy validate --config /tmp/Caddyfile.www-proposed --adapter caddyfile
```

Review the whole-file diff against the saved live backup before any separately
authorized apply. The lint is an offline guard; it does not replace Caddy v2.11.4
validation with the real node-local certificates and mounts.
