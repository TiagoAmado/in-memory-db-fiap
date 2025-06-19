from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis
from typing import List
import os

app = FastAPI()

class Question(BaseModel):
    question_text: str
    question_id: int
    alternativa_a: str
    alternativa_b: str
    alternativa_c: str
    alternativa_d: str
    alternativa_correta: str
    dificuldade: str
    assunto: str

class Answer(BaseModel):
    question_id: int
    alternativa_escolhida: str
    datahora: str
    usuario: str
    nro_tentativa: int  # Adicionado aqui

REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

def get_redis_connection():
    try:
        return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    except redis.RedisError as e:
        raise HTTPException(status_code=500, detail="Could not connect to Redis")

# --- QUESTION TAG ---

# GET
@app.get("/question/{question_key}", tags=["question"])
def get_question(question_key: str):
    r = get_redis_connection()
    question = r.hgetall("question:" + question_key)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question

@app.get("/questions", tags=["question"])
def get_all_questions():
    r = get_redis_connection()
    keys = r.keys("question:*")
    questions = []
    for key in keys:
        question = r.hgetall(key)
        question['key'] = key
        questions.append(question)
    return questions

# POST
@app.post("/question", tags=["question"])
def create_question(question: Question):
    r = get_redis_connection()
    if not save_question(r, question):
        raise HTTPException(status_code=400, detail="Question already exists")
    return {"message": "Question has been created"}

@app.post("/questions", tags=["question"])
def create_questions(questions: List[Question]):
    r = get_redis_connection()
    created = []
    errors = []
    for question in questions:
        if save_question(r, question):
            created.append(question.question_id)
        else:
            errors.append({"question_id": question.question_id, "error": "Question already exists"})
    return {"created": created, "errors": errors}

# PUT
@app.put("/question/{question_key}", tags=["question"])
def update_question(question_key: str, question: Question):
    r = get_redis_connection()
    if r.hgetall("question:" + question_key) == {}:
        raise HTTPException(status_code=404, detail="Question not found")
    r.hset("question:" + question_key, "question_text", question.question_text,)
    return {"message": "Question has been updated"}

# DELETE
@app.delete("/question/{question_key}", tags=["question"])
def delete_question(question_key: str):
    r = get_redis_connection()
    if r.hgetall("question:" + question_key) == {}:
        raise HTTPException(status_code=404, detail="Question not found")
    r.delete("question:" + question_key)
    return {"message": "Question has been deleted"}

@app.delete("/questions", tags=["question"])
def delete_all_questions():
    r = get_redis_connection()
    keys = r.keys("question:*")
    deleted = 0
    for key in keys:
        r.delete(key)
        deleted += 1
    return {"message": f"{deleted} questions have been deleted"}

# --- ANSWER TAG ---

# GET
@app.get("/answer/{question_key}", tags=["answer"])
def get_answer(question_key: str):
    r = get_redis_connection()
    answer = r.hgetall("answer:" + question_key)
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    return answer

@app.get("/answers", tags=["answer"])
def get_all_answers():
    r = get_redis_connection()
    keys = r.keys("answer:*")
    answers = []
    for key in keys:
        answer = r.hgetall(key)
        answer['key'] = key
        # Recupera a alternativa correta da questão correspondente
        question_id = answer.get("question_id")
        question = r.hgetall(f"question:{question_id}")
        alternativa_correta = question.get("alternativa_correta")
        # Adiciona o campo is_correct
        answer['is_correct'] = (
            answer.get('alternativa_escolhida') == alternativa_correta
            if alternativa_correta else False
        )
        answers.append(answer)
    return answers

# POST
@app.post("/answer", tags=["answer"])
def create_answer(answer: Answer):
    r = get_redis_connection()
    answer_key = f"answer:{answer.usuario}:{answer.question_id}:{answer.nro_tentativa}"
    if r.hget(answer_key, "alternativa_escolhida") is not None:
        raise HTTPException(status_code=400, detail="Answer already exists")

    r.hset(
        answer_key,
        mapping={
            'alternativa_escolhida': answer.alternativa_escolhida,
            'datahora': answer.datahora,
            'usuario': answer.usuario,
            'nro_tentativa': answer.nro_tentativa
        }
    )
    return {"message": "Answer has been created"}

@app.post("/answers", tags=["answer"])
def create_answers(answers: List[Answer]):
    r = get_redis_connection()
    created = []
    errors = []
    for answer in answers:
        answer_key = f"answer:{answer.usuario}:{answer.question_id}:{answer.nro_tentativa}"
        if r.hget(answer_key, "alternativa_escolhida") is not None:
            errors.append({
                "usuario": answer.usuario,
                "question_id": answer.question_id,
                "nro_tentativa": answer.nro_tentativa,
                "error": "Answer already exists"
            })
            continue
        r.hset(
            answer_key,
            mapping={
                'alternativa_escolhida': answer.alternativa_escolhida,
                'question_id': answer.question_id,
                'datahora': answer.datahora,
                'usuario': answer.usuario,
                'nro_tentativa': answer.nro_tentativa
            }
        )
        created.append({
            "usuario": answer.usuario,
            "question_id": answer.question_id,
            "nro_tentativa": answer.nro_tentativa
        })
    return {"created": created, "errors": errors}

# PUT
@app.put("/answer/{question_key}", tags=["answer"])
def update_answer(question_key: str, answer: Answer):
    r = get_redis_connection()
    if r.hgetall("answer:" + question_key) == {}:
        raise HTTPException(status_code=404, detail="Answer not found")
    r.hset("answer:" + question_key, "alternativa_escolhida", answer.alternativa_escolhida,)
    return {"message": "Answer has been updated"}

# DELETE
@app.delete("/answer/{question_key}", tags=["answer"])
def delete_answer(question_key: str):
    r = get_redis_connection()
    if r.hgetall("answer:" + question_key) == {}:
        raise HTTPException(status_code=404, detail="Answer not found")
    r.delete("answer:" + question_key)
    return {"message": "Answer has been deleted"}

@app.delete("/answers", tags=["answer"])
def delete_all_answers():
    r = get_redis_connection()
    keys = r.keys("answer:*")
    deleted = 0
    for key in keys:
        r.delete(key)
        deleted += 1
    return {"message": f"{deleted} answers have been deleted"}

# --- HEALTH CHECK TAG ---

@app.get("/", tags=["health check"])
def read_root():
    return {"Hello": "API de teste do lab de redis com python Quiz"}

def save_question(r, question: Question):
    key = f"question:{question.question_id}"
    if r.hget(key, "question_text") is not None:
        return False
    r.hset(
        key,
        mapping={
            'question_text': question.question_text,
            'alternativa_a': question.alternativa_a,
            'alternativa_b': question.alternativa_b,
            'alternativa_c': question.alternativa_c,
            'alternativa_d': question.alternativa_d,
            'alternativa_correta': question.alternativa_correta,
            'dificuldade': question.dificuldade,
            'assunto': question.assunto
        }
    )
    return True 