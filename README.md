# in_memory_project 🚀

A unified environment for ingesting quiz data via FastAPI and Redis, persisting it to Postgres, and visualizing it with Metabase.

---

## 🛠️ Requirements
- [Docker](https://www.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)

---

## ▶️ How to Start Everything

1. **Start all services:**
   ```sh
   docker-compose up -d
   ```
   This will start:
   - Redis (in-memory database)
   - Postgres (persistent database)
   - FastAPI (quiz API)
   - Ingestion worker (moves data from Redis to Postgres)
   - Metabase (dashboard)

2. **Access the API:**
   - Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Example endpoints:
     - `POST /questions` (bulk load questions)
     - `POST /answers` (bulk load answers)

3. **Populate Redis with Example Data:**
   - Use the files in `carga-dados-fake/`:
     - `questions.json`
     - `answers.json`
   - You can POST these via Swagger UI or with curl/Postman:
     ```sh
     curl -X POST "http://localhost:8000/questions" -H "Content-Type: application/json" -d @carga-dados-fake/questions.json
     curl -X POST "http://localhost:8000/answers" -H "Content-Type: application/json" -d @carga-dados-fake/answers.json
     ```

4. **Dashboard:**
   - Metabase: [http://localhost:3000](http://localhost:3000)
   - Complete the initial setup wizard
   - When prompted to add your data:
     - Select PostgreSQL as the database type
     - Host: `db-dw`
     - Port: `5432`
     - Database name: `dw`
     - Username: `dw_user`
     - Password: `dw_password`
   - Start exploring and visualizing your data!

---

## 🧹 Cleaning Up
- Stop everything: `docker-compose down`
- Remove all data/volumes: `docker-compose down -v`

---

## 📚 References
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Redis Documentation](https://redis.io/documentation/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
- [Metabase Documentation](https://www.metabase.com/docs/)

---

## Project Structure

```
in_memory_project/
│
├── docker-compose.yml
├── README.md
├── .gitignore
│
├── api/                  # FastAPI app (questions/answers API)
│   └── main.py
│   └── requirements.txt
│
├── ingestion/            # Redis-to-Postgres worker
│   └── worker.py
│   └── requirements.txt
│
└── carga-dados-fake/     # Example data for ingestion
    └── questions.json
    └── answers.json
```

---

> Siga as melhores práticas de segurança e não exponha suas credenciais em ambientes públicos. 