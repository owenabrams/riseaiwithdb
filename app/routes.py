from flask import Blueprint, request
from twilio.twiml.messaging_response import MessagingResponse
from .models import Message
from . import db
import openai
from elasticsearch import Elasticsearch, NotFoundError
import os

main = Blueprint('main', __name__)

openai.api_key = os.environ.get('OPENAI_API_KEY')

es = None
if os.environ.get('USE_ELASTICSEARCH') == 'True':
    es = Elasticsearch([{'host': 'localhost', 'port': 9200}])

def generate_answer(question):
    try:
        if es:
            response = es.search(index='documents', body={'query': {'match': {'content': question}}})
            hits = response['hits']['hits']
            if hits:
                content = ' '.join([hit['_source']['content'] for hit in hits])
                prompt = f"Q: {question}\nA: {content}"
            else:
                prompt = f"Q: {question}\nA:"
        else:
            prompt = f"Q: {question}\nA:"

        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=150
        )

        return response.choices[0].text.strip()

    except Exception as e:
        print(f"Error generating answer: {e}")
        return "I'm sorry, I couldn't process your request."

@main.route('/chatgpt', methods=['POST'])
def chatgpt():
    if request.method == 'POST':
        incoming_que = request.values.get('Body', '').lower()
        print("Question: ", incoming_que)
        answer = generate_answer(incoming_que)
        print("BOT Answer: ", answer)

        # Store the conversation in the database
        new_message = Message(user_message=incoming_que, bot_response=answer)
        db.session.add(new_message)
        db.session.commit()

        bot_resp = MessagingResponse()
        msg = bot_resp.message()
        msg.body(answer)
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
