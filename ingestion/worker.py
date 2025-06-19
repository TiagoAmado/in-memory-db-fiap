import time
import redis
import psycopg2
import json
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connection settings from environment variables
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

PG_HOST = os.getenv('PG_HOST', 'postgres')
PG_PORT = int(os.getenv('PG_PORT', 5432))
PG_DB = os.getenv('PG_DB', 'dw')
PG_USER = os.getenv('PG_USER', 'user')
PG_PASSWORD = os.getenv('PG_PASSWORD', 'senhaForte2025')

def create_tables_if_not_exist(conn):
    with conn.cursor() as cur:
        # Create questions table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id SERIAL PRIMARY KEY,
                question_id INTEGER UNIQUE,
                question_text TEXT,
                option_a TEXT,
                option_b TEXT,
                option_c TEXT,
                option_d TEXT,
                correct_option CHAR(1),
                difficulty TEXT,
                subject TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create answers table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS answers (
                id SERIAL PRIMARY KEY,
                user_id TEXT,
                question_id INTEGER,
                attempt_number INTEGER,
                answer_text CHAR(1),
                is_correct BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, question_id, attempt_number)
            );
        """)
    conn.commit()
    logger.info("Database tables created/verified successfully")

def process_question(conn, redis_conn, question_key):
    try:
        question_data = redis_conn.hgetall(question_key)
        if not question_data:
            return False
        
        question_id = int(question_key.split(':')[1])
        
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO questions (
                    question_id, question_text, 
                    option_a, option_b, option_c, option_d,
                    correct_option, difficulty, subject
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (question_id) DO NOTHING
                RETURNING question_id;
            """, (
                question_id,
                question_data.get('question_text'),
                question_data.get('alternativa_a'),
                question_data.get('alternativa_b'),
                question_data.get('alternativa_c'),
                question_data.get('alternativa_d'),
                question_data.get('alternativa_correta'),
                question_data.get('dificuldade'),
                question_data.get('assunto')
            ))
            
        conn.commit()
        logger.info(f"Processed question {question_id}")
        
    except Exception as e:
        logger.error(f"Error processing question {question_key}: {str(e)}")
        conn.rollback()
        return False

def process_answer(conn, redis_conn, answer_key):
    try:
        answer_data = redis_conn.hgetall(answer_key)
        if not answer_data:
            return False
            
        # Parse answer key format: answer:user_id:question_id:attempt
        parts = answer_key.split(':')
        user_id = parts[1]
        question_id = int(parts[2])
        attempt = int(parts[3])
        
        # Get question's correct answer
        with conn.cursor() as cur:
            cur.execute("SELECT correct_option FROM questions WHERE question_id = %s", (question_id,))
            result = cur.fetchone()
            if not result:
                logger.warning(f"Question {question_id} not found for answer {answer_key}")
                return False
                
            correct_option = result[0]
            answer_option = answer_data.get('alternativa_escolhida', '')
            is_correct = answer_option.lower() == correct_option.lower() if answer_option else False
            
            cur.execute("""
                INSERT INTO answers (user_id, question_id, attempt_number, answer_text, is_correct)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id, question_id, attempt_number) DO NOTHING
                RETURNING id;
            """, (user_id, question_id, attempt, answer_option, is_correct))
            
        conn.commit()
        logger.info(f"Processed answer for user {user_id}, question {question_id}, attempt {attempt}")
        
    except Exception as e:
        logger.error(f"Error processing answer {answer_key}: {str(e)}")
        conn.rollback()
        return False

def main():
    max_retries = 5
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            # Connect to Redis
            redis_conn = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
            redis_conn.ping()  # Test connection
            logger.info("Connected to Redis successfully")
            
            # Connect to Postgres
            pg_conn = psycopg2.connect(
                host=PG_HOST,
                port=PG_PORT,
                dbname=PG_DB,
                user=PG_USER,
                password=PG_PASSWORD
            )
            logger.info("Connected to PostgreSQL successfully")
            
            # Create tables
            create_tables_if_not_exist(pg_conn)
            
            # Main processing loop
            logger.info("Starting main processing loop...")
            while True:
                processed_something = False
                
                # Process questions
                question_keys = redis_conn.keys('question:*')
                for key in question_keys:
                    if process_question(pg_conn, redis_conn, key):
                        processed_something = True
                
                # Process answers
                answer_keys = redis_conn.keys('answer:*')
                for key in answer_keys:
                    if process_answer(pg_conn, redis_conn, key):
                        processed_something = True
                
                # If nothing was processed, wait longer before next check
                if not processed_something:
                    logger.info("No new data to process, waiting...")
                    time.sleep(30)  # Wait 30 seconds before checking again
                else:
                    time.sleep(1)  # Quick check for new data
                
        except redis.ConnectionError as e:
            logger.error(f"Redis connection error: {str(e)}")
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            
        if attempt < max_retries - 1:
            logger.info(f"Retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
            time.sleep(retry_delay)
        else:
            logger.error("Max retries reached. Exiting.")
            break

if __name__ == "__main__":
    main() 