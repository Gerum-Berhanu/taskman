# Project structure

```
taskman/
├── README.md           # how to run the product
├── .gitignore
├── pyproject.toml      # uv project + dependencies
├── uv.lock
├── .env.example        # safe template for env vars
├── app/                # application package
│   ├── main.py         # FastAPI app
│   ├── config.py       # settings
│   ├── database.py     # engine / session
│   ├── models.py       # DB models
│   ├── schemas.py      # API schemas
│   ├── exceptions.py   # custom error handlers (optional)
│   └── routers/        # HTTP endpoints
├── tests/              # automated tests
└── docs/               # handbook
```

**Flow**

```
Request → routers → schemas → models + database → SQLite
Response ← schemas ← ...
```

- Routers handle HTTP only.
- Schemas = API contract; models = DB shape.

Project title: Taskman
