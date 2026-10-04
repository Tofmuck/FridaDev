"""M1 contexts and explicit M2 read/adopt actions; preparation stays absent."""
from flask import jsonify, request
from core import document_workshop_context_service as service
from core import workspace_document_adoption_service as adoption


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

    @app.get('/api/workspace-folders/<folder_id>/documents/remote')
    def list_remote_workspace_documents(folder_id):
        data = request.args.to_dict() if all(len(request.args.getlist(key)) == 1 for key in request.args) else None
        payload, status = adoption.list_remote(folder_id, data, **dependencies())
        return jsonify(payload), status

    @app.post('/api/workspace-folders/<folder_id>/documents/adopt')
    def adopt_remote_workspace_document(folder_id):
        payload, status = adoption.adopt_remote(folder_id, request.get_json(silent=True), **dependencies())
        return jsonify(payload), status
