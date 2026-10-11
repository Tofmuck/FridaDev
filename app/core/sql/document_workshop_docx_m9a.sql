-- M9-A explicit additive capability; never applied by startup or a request.
-- Existing canonical/Markdown hashes and all immutable histories are preserved.
ALTER TABLE document_actions DROP CONSTRAINT IF EXISTS document_actions_format_check;
ALTER TABLE document_actions ADD CONSTRAINT document_actions_format_check CHECK (format IN ('markdown','docx'));
ALTER TABLE document_receipts DROP CONSTRAINT IF EXISTS document_receipts_format_check;
ALTER TABLE document_receipts ADD CONSTRAINT document_receipts_format_check CHECK (format IN ('markdown','docx'));
ALTER TABLE document_revision_renders DROP CONSTRAINT IF EXISTS document_revision_renders_format_check;
ALTER TABLE document_revision_renders ADD CONSTRAINT document_revision_renders_format_check CHECK (format IN ('markdown','docx'));
ALTER TABLE document_revision_renders DROP CONSTRAINT IF EXISTS document_revision_renders_serializer_version_check;
ALTER TABLE document_revision_renders ADD CONSTRAINT document_revision_renders_serializer_version_check CHECK
 ((format='markdown' AND serializer_version='frida_markdown_v1') OR (format='docx' AND serializer_version='frida_writer_v1'));
ALTER TABLE document_execution_journal DROP CONSTRAINT IF EXISTS document_execution_journal_serializer_version_check;
ALTER TABLE document_execution_journal ADD CONSTRAINT document_execution_journal_serializer_version_check CHECK
 (serializer_version IN ('frida_markdown_v1','frida_writer_v1'));
