## Directory Structure

```
tests/
├── rhosocial/
│   └── activerecord/
│       └── backend/
│           └── mysql80/
│               ├── config.template.yaml
│               ├── config.yaml (ignored)
│               ├── README.md
│               ├── test_....yaml
```

## Test Configuration
Before running tests, you need to:
1. Copy `config.template.yaml` to `config.yaml` in the same directory
2. Modify the configuration parameters (host, port, database, username, password) according to your actual MySQL setup
3. Ensure each configuration has a unique `label` value
4. You can prepare multiple versions of configurations as needed, just make sure their labels are unique
