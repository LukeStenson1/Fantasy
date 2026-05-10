# Auth Testing Playbook

## Step 1: MongoDB Verification
```
mongosh
use fantasy_reference_db
db.users.find({role: "admin"}).pretty()
```
Verify: bcrypt hash starts with `$2b$`, indexes exist on users.email (unique), login_attempts.identifier, password_reset_tokens.expires_at (TTL).

## Step 2: API Testing
```
curl -c cookies.txt -X POST http://localhost:8001/api/auth/login -H "Content-Type: application/json" -d '{"email":"admin@ffref.com","password":"admin123"}'
cat cookies.txt
curl -b cookies.txt http://localhost:8001/api/auth/me
```

Login should return user object and set `access_token` + `refresh_token` cookies. The `/me` call should return same user using cookies.

## Test Users
- admin@ffref.com / admin123
- user@ffref.com / user123
