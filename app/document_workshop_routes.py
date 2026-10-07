"""Workshop contexts, adoption, durable actions and confirmed M6 execution."""
from io import BytesIO
from flask import jsonify, request, send_file
from core import document_workshop_context_service as service
from core import workspace_document_adoption_service as adoption
from core import document_workshop_actions as actions
from core.document_workshop_contract import DocumentWorkshopError


def register_document_workshop_routes(app, *, get_store, get_conversations, get_folders, get_files,
                                      get_executor=None):
    def executor():
        return get_executor() if get_executor is not None else None

    def project_action(record):
        if not record:
            return record
        available=executor()
        if record.get('operation')=='update' and record.get('state')=='remote_uncertain' and getattr(available,'supports_update',False):
            available.reconcile(record['id'])
            record=actions.get_action(record['id'])
        from core.document_workshop_execution_service import project_action as project
        return project(record, executor=available)

    def dependencies():
        return dict(store=get_store(), conversations=get_conversations(), folders=get_folders(), files=get_files())

    @app.post('/api/document-workshop/contexts')
    def create_document_workshop_context():
        payload, status = service.create_context(request.get_json(silent=True), **dependencies())
        if status == 201:
            payload['context']['capabilities'] = actions.capabilities(executor())
        return jsonify(payload), status

    @app.get('/api/document-workshop/contexts/<context_id>')
    def get_document_workshop_context(context_id):
        payload, status = service.get_context(context_id, **dependencies())
        if status == 200:
            try:
                payload['context']['preparation'] = project_action(actions.latest(payload['context']['id']))
                payload['context']['capabilities'] = actions.capabilities(executor())
            except Exception:
                return jsonify(ok=False, reason_code='document_action_storage_unavailable'), 503
        return jsonify(payload), status

    def action_response(action_id, cancel=False):
        action_id = service._id(action_id)
        data = request.get_json(silent=True) if cancel else None
        if not action_id or (cancel and (type(data) is not dict or set(data) != {'context_id'}
                                        or not service._id(data['context_id']))):
            return jsonify(ok=False, reason_code='document_action_request_invalid'), 400
        try:
            action = actions.cancel(action_id, service._id(data['context_id'])) if cancel else actions.get_action(action_id)
            if not action:
                return jsonify(ok=False, reason_code='document_action_missing'), 404
            return jsonify(ok=True, action=project_action(action)), 200
        except DocumentWorkshopError as exc:
            return jsonify(ok=False, reason_code=exc.reason_code), 404 if exc.reason_code == 'document_action_missing' else 409
        except Exception:
            return jsonify(ok=False, reason_code='document_action_storage_unavailable'), 503

    @app.get('/api/document-workshop/actions/<action_id>')
    def get_document_workshop_action(action_id):
        return action_response(action_id)

    @app.post('/api/document-workshop/actions/<action_id>/cancel')
    def cancel_document_workshop_action(action_id):
        return action_response(action_id, cancel=True)

    @app.post('/api/document-workshop/actions/<action_id>/confirm')
    def confirm_document_workshop_action(action_id):
        available = executor()
        if available is None:
            return jsonify(ok=False, reason_code='document_execution_unavailable'), 503
        from core.document_workshop_execution_service import confirm
        payload, status = confirm(action_id, request.get_json(silent=True), executor=available)
        return jsonify(payload), status

    @app.get('/api/workspace-folders/<folder_id>/files/<file_id>/content')
    def get_document_workshop_file_content(folder_id, file_id):
        if request.args:
            return jsonify(ok=False, reason_code='document_file_request_invalid'), 400
        from core.document_workshop_receipts import read_content
        try:
            content, name = read_content(folder_id, file_id)
            response = send_file(BytesIO(content), mimetype='text/plain; charset=utf-8',
                as_attachment=True, download_name=name, max_age=0)
            response.headers['Cache-Control'] = 'private, no-store'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            return response
        except DocumentWorkshopError as error:
            return jsonify(ok=False, reason_code=error.reason_code), 404 if error.reason_code=='document_file_missing' else 503
        except Exception:
            return jsonify(ok=False, reason_code='document_file_unavailable'), 503

    @app.get('/api/workspace-folders/<folder_id>/documents/remote')
    def list_remote_workspace_documents(folder_id):
        data = request.args.to_dict() if all(len(request.args.getlist(key)) == 1 for key in request.args) else None
        payload, status = adoption.list_remote(folder_id, data, **dependencies())
        return jsonify(payload), status

    @app.post('/api/workspace-folders/<folder_id>/documents/adopt')
    def adopt_remote_workspace_document(folder_id):
        payload, status = adoption.adopt_remote(folder_id, request.get_json(silent=True), **dependencies())
        return jsonify(payload), status
