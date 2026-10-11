"""M9-A uses the existing native HTTP harness with its actual DOCX composition."""
from tests.support.document_workshop_m6_http import main

if __name__ == "__main__":
    main(m7=True,m9=True)
