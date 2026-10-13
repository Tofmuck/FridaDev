-- M10 explicit additive PDF publication capability, after M9-A; never startup.
-- Canonical, revisions, journal and existing publications remain unchanged.
ALTER TABLE document_actions DROP CONSTRAINT IF EXISTS document_actions_format_check;
ALTER TABLE document_actions ADD CONSTRAINT document_actions_format_check CHECK (format IN ('markdown','docx','pdf'));
ALTER TABLE document_receipts DROP CONSTRAINT IF EXISTS document_receipts_format_check;
ALTER TABLE document_receipts ADD CONSTRAINT document_receipts_format_check CHECK (format IN ('markdown','docx','pdf'));
ALTER TABLE document_revision_renders DROP CONSTRAINT IF EXISTS document_revision_renders_format_check;
ALTER TABLE document_revision_renders ADD CONSTRAINT document_revision_renders_format_check CHECK (format IN ('markdown','docx','pdf'));
ALTER TABLE document_revision_renders DROP CONSTRAINT IF EXISTS document_revision_renders_serializer_version_check;
ALTER TABLE document_revision_renders ADD CONSTRAINT document_revision_renders_serializer_version_check CHECK
 ((format='markdown' AND serializer_version='frida_markdown_v1') OR (format IN ('docx','pdf') AND serializer_version='frida_writer_v1'));
