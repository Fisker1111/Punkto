# Deployment Smoke Tests

```bash
NODE=127.0.0.1:18080

curl -fsS "http://$NODE/health"
curl -fsS "http://$NODE/node/info"
curl -fsS "http://$NODE/publication/root.json"
```

Expected:
- HTTP 200 for all endpoints.
- `root.json` contains `v`, `seq`, and `head`.
- Browser can read publication and publish via `/submit`.
