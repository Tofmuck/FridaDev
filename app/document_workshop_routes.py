"""Thin M1 HTTP composition. Preparation routes are deliberately absent."""
from flask import jsonify, request
from core import document_workshop_context_service as service


def register_document_workshop_routes(app, *, get_store, get_conversations, get_folders, get_files):
    def dependencies():
        return dict(store=get_store(), conversations=get_conversations(), folders=get_folders(), files=get_files())

    @app.post('/api/document-workshop/contexts')
    def create_document_workshop_context():
        payload, status = service.create_context(request.get_json(silent=True), **dependencies())
        return jsonify(payload), status

    @app.get('/api/document-workshop/contexts/<context_id>')
    def get_document_workshop_context(context_id):
        payload, status = service.get_context(context_id, **dependencies())
        return jsonify(payload), status
