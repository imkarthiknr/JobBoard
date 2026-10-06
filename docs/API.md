# REST API examples

Base URL: `http://localhost:8000/api/v1`. Interactive docs are at `/docs` while the app is running.

Errors use FastAPI's standard shape: `{"detail": "message"}`. Validation errors (`422`) return a list of `{loc, msg, type}` objects.

## Register and log in

```bash
curl -X POST http://localhost:8000/api/v1/users \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","email":"alice@example.com","password":"s3cret-pass"}'
# 201 {"id":2,"username":"alice","email":"alice@example.com","is_active":true,"created_at":"…"}

TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token \
  -d 'username=alice&password=s3cret-pass' | jq -r .access_token)
```

| Rule       | Constraint                                                                 |
| ---------- | -------------------------------------------------------------------------- |
| `username` | 3–50 characters: letters, digits, `.`, `_`, `-`. Unique, case-insensitive |
| `email`    | Valid address. Stored lower-cased and unique                               |
| `password` | 8–72 bytes with at least one letter and one digit                          |

`POST /users` returns `409` if the username or email is taken. `POST /auth/token` returns `401` for bad credentials or an inactive account.

## Search jobs

```bash
curl 'http://localhost:8000/api/v1/jobs?q=python&location=india&page=1&size=10'
```

```json
{
  "items": [
    {
      "id": 1,
      "title": "Senior Backend Engineer (Python)",
      "company": "Kaveri Labs",
      "company_url": null,
      "location": "Chennai, India",
      "description": "…",
      "date_posted": "2026-10-06",
      "is_active": true,
      "owner_id": 1
    }
  ],
  "total": 1,
  "page": 1,
  "size": 10,
  "pages": 1
}
```

- `q` matches the title, company or description, case-insensitively. `%` and `_` are matched literally.
- `location` is a case-insensitive substring match.
- `size` is between 1 and 50. Only active jobs are listed, newest first.

## Post, update and delete

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"Backend Engineer","company":"Acme","company_url":"https://acme.example",
       "location":"Remote","description":"Build and run our Python services."}'
# 201, Location: /api/v1/jobs/11

curl -X PATCH http://localhost:8000/api/v1/jobs/11 \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"is_active": false}'          # close the posting

curl -X DELETE http://localhost:8000/api/v1/jobs/11 -H "Authorization: Bearer $TOKEN"   # 204
```

| Field         | Constraint                         |
| ------------- | ---------------------------------- |
| `title`       | 2–120 characters                   |
| `company`     | 1–120 characters                   |
| `company_url` | Optional absolute `http(s)` URL    |
| `location`    | 2–120 characters                   |
| `description` | 10–10,000 characters               |

`PATCH` and `DELETE` return `403` unless you own the job or are a superuser. A closed job returns `404` to everyone except its owner and superusers.
