# API Test Guide

Base URL: `http://localhost:8000`

Run the server first:
```bash
cd src && uv run uvicorn main:app --reload
```

---

## 1. Sign up

```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "secret123", "name": "Test User"}'
```

Save the `access_token` from the response — you'll need it for all file requests.

```bash
TOKEN="<paste_access_token_here>"
```

---

## 2. Upload a text file

Create a sample file:
```bash
echo "The Eiffel Tower was built in 1889 in Paris, France. It stands 330 meters tall.
Gustave Eiffel designed it as the entrance arch for the 1889 World's Fair.
Today it is the most visited monument in the world, attracting millions of tourists each year.
The tower was almost demolished in 1909 but was saved because it served as a radio transmission tower." > /tmp/sample.txt
```

Upload it:
```bash
curl -X POST http://localhost:8000/files \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/sample.txt;type=text/plain"
```

Upload a second file for richer search results:
```bash
echo "Python is a high-level programming language created by Guido van Rossum in 1991.
It emphasizes code readability and supports multiple programming paradigms.
Python is widely used in data science, machine learning, and web development.
The language uses indentation to define code blocks instead of curly braces." > /tmp/python.txt

curl -X POST http://localhost:8000/files \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/python.txt;type=text/plain"
```

---

## 3. List files

```bash
curl http://localhost:8000/files \
  -H "Authorization: Bearer $TOKEN"
```

---

## 4. Search (hybrid FTS + vector RRF)

```bash
# Should return the Eiffel Tower file
curl "http://localhost:8000/files/search?q=Paris+tower&limit=5" \
  -H "Authorization: Bearer $TOKEN"

# Should return the Python file
curl "http://localhost:8000/files/search?q=programming+language&limit=5" \
  -H "Authorization: Bearer $TOKEN"

# Semantic query — no exact keyword match, relies on vector leg
curl "http://localhost:8000/files/search?q=famous+landmark+in+Europe&limit=5" \
  -H "Authorization: Bearer $TOKEN"
```

The `rank` field in results is the RRF score. Higher = more relevant.

---

## 5. Get a single file

```bash
curl http://localhost:8000/files/1 \
  -H "Authorization: Bearer $TOKEN"
```

---

## 6. Get file content

```bash
curl http://localhost:8000/files/1/content \
  -H "Authorization: Bearer $TOKEN"
```

---

## 7. Delete a file

```bash
curl -X DELETE http://localhost:8000/files/1 \
  -H "Authorization: Bearer $TOKEN"
```

---

## Verify chunks in the DB

Connect to your Postgres instance and inspect:

```sql
-- See all chunks for a file
SELECT id, chunk_index, text, model FROM chunks WHERE file_id = 1 ORDER BY chunk_index;

-- Check embeddings were stored (first 5 dims)
SELECT id, chunk_index, embedding[1:5] FROM chunks WHERE file_id = 1;

-- Count chunks per file
SELECT file_id, COUNT(*) AS chunk_count FROM chunks GROUP BY file_id;
```


## INFO ABOUT RARES

RARES IS REAAAALY COOL and he is 22.