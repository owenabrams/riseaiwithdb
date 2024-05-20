from flask import request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
import openai
import logging
from elasticsearch import Elasticsearch, ElasticsearchException, ConnectionError
from . import db
from .models import User, Question, Answer
from datetime import datetime

openai.api_key = 'YOUR_OPENAI_API_KEY'

try:
    es = Elasticsearch([{'host': 'localhost', 'port': 9200}])
    es.ping()
    elasticsearch_available = True
except (ElasticsearchException, ConnectionError):
    elasticsearch_available = False

def retrieve_relevant_content(query):
    if not elasticsearch_available:
        return []

    try:
        response = es.search(index='content', body={
            'query': {
                'match': {
                    'body': query
                }
            }
        })
        return response['hits']['hits']
    except ElasticsearchException as e:
        logging.error(f"Error retrieving content: {e}")
        return []

def generate_rag_answer(question):
    relevant_content = retrieve_relevant_content(question)
    if relevant_content:
        context = "\n\n".join([hit['_source']['body'] for hit in relevant_content])
        prompt = f"Context: {context}\n\nQuestion: {question}"
    else:
        prompt = f"Question: {question}"

    try:
        response = openai.Completion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        answer = response.choices[0].message['content'].strip()
        return answer
    except Exception as e:
        logging.error(f"Error generating answer: {e}")
        return "I'm sorry, I couldn't process your request."

from . import create_app

app = create_app()

@app.route('/chatgpt', methods=['POST', 'GET'])
def chatgpt():
    if request.method == 'POST':
        whatsapp_id = request.values.get('From', '')
        question_text = request.values.get('Body', '').lower()

        user = User.query.filter_by(whatsapp_id=whatsapp_id).first()
        if not user:
            user = User(whatsapp_id=whatsapp_id, name="Unknown")
            db.session.add(user)
            db.session.commit()

        question = Question(user_id=user.id, question=question_text)
        db.session.add(question)
        db.session.commit()

        answer_text = generate_rag_answer(question_text)

        answer = Answer(question_id=question.id, answer=answer_text)
        db.session.add(answer)
        db.session.commit()

        logging.info(f"Question: {question_text}")
        logging.info(f"BOT Answer: {answer_text}")

        bot_resp = MessagingResponse()
        msg = bot_resp.message()
        msg.body(answer_text)

        return str(bot_resp)
    else:
        return "This endpoint is for POST requests from Twilio."

@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    question_text = data.get('question', '').lower()

    user = User.query.filter_by(whatsapp_id='web_user').first()
    if not user:
        user = User(whatsapp_id='web_user', name='Web User')
        db.session.add(user)
        db.session.commit()

    question = Question(user_id=user.id, question=question_text)
    db.session.add(question)
    db.session.commit()

    answer_text = generate_rag_answer(question_text)

    answer = Answer(question_id=question.id, answer=answer_text)
    db.session.add(answer)
    db.session.commit()

    logging.info(f"Question: {question_text}")
    logging.info(f"BOT Answer: {answer_text}")

    return jsonify({'answer': answer_text})

@app.route('/')
def home():
    return "This is a WhatsApp chatbot powered by GPT-3.5-turbo. Use the /chatgpt endpoint to interact with the bot."
