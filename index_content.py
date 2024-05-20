import os
from elasticsearch import Elasticsearch, ElasticsearchException
from app import create_app, db
from app.models import Content

# Initialize the Flask app
app = create_app()
app.app_context().push()

# Initialize Elasticsearch
es = Elasticsearch([{'host': 'localhost', 'port': 9200}])

def index_content(content):
    try:
        es.index(index='content', id=content.id, body={
            'title': content.title,
            'body': content.body,
            'created_at': content.created_at
        })
    except ElasticsearchException as e:
        print(f"Failed to index content: {e}")

def index_all_content():
    contents = Content.query.all()
    for content in contents:
        index_content(content)
    print(f"Indexed {len(contents)} content items.")

if __name__ == "__main__":
    index_all_content()
